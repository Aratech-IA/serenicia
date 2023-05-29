# -*- coding: utf-8 -*-

import os
import time
import pytz
import json
import logging
import secrets
import psutil as ps
import hashlib

from crontab import CronTab
from threading import Thread
from subprocess import Popen, STDOUT
from PIL import Image, ImageFont, ImageDraw
from django.core.exceptions import ObjectDoesNotExist

from django.template.loader import render_to_string

from django.core.mail import send_mail, BadHeaderError

from django.contrib.auth import login
from django.contrib.auth.models import User
from django.contrib.auth.forms import PasswordResetForm
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.decorators import login_required, permission_required

from django.utils import timezone
from django.utils import translation
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.utils.translation import gettext_lazy as _

from django.conf import settings
from django.shortcuts import render, redirect
from django.http import HttpResponseRedirect, HttpResponse

from django.db.models import Count
from django.db import IntegrityError
from django.db.models.query_utils import Q

from .log import Logger
from .forms import AlertForm, AutomatForm, ArchiveForm, PreferencesForm, FilterForm
from .models import Camera, Result, Alert, Client, Alert_type, Profile, Telegram, ALERT_CHOICES, local_to_utc, \
    utc_to_local, CameraUri, Preferences, AlertStuffsChoice

from django.urls import reverse
from datetime import datetime, timedelta

if 'log_views' not in globals():
    log_views = Logger('views', level=logging.ERROR).run()

if "serenicia" in settings.DOMAIN.lower():
    from app4_ehpad_base.models import PreferencesSerenicia
    from app4_ehpad_base.forms import PreferencesSereniciaForm


def face_reco_login(request):
    if request.POST.get('identified_user'):
        folder, _, _ = request.POST.get('identified_user').split('/')
        identified_user = User.objects.get(profileserenicia__folder=folder)
        return render(request, 'app1_base/face_reco_login_validation.html', {'identified_user': identified_user})
    elif 'valid.x' in request.POST:
        user = User.objects.get(profileserenicia__folder=request.POST.get('user_folder'))
        login(request, user, backend='django.contrib.auth.backends.ModelBackend')
        if settings.DOMAIN.lower() == 'serenicia':
            return redirect('app4_ehpad_base index')
        else:
            return redirect('app1_base index')
    elif 'invalid.x' in request.POST:
        return redirect(settings.LOGIN_REDIRECT_URL)
    return render(request, 'app1_base/face_reco_login.html')


def process(key):
    for p in ps.process_iter():
        try:
            for n in p.cmdline():
                if key in n:
                    return p
        except ps.AccessDenied:
            pass
    return False


def is_client_connected(client, client_search=False):
    if client_search:
        client = Client.objects.get(pk=client)
    delay = datetime.now(pytz.utc) - client.timestamp
    if delay > timedelta(seconds=20):
        return False
    return True


def index(request):
    if not request.user.has_perm('app0_access.view_family'):
        request.session['resident_id'] = None
    user_language = 'fr'
    translation.activate(user_language)
    # request.session[translation.LANGUAGE_SESSION_KEY] = user_language
    request.session['django_timezone'] = 'Europe/Paris'
    if not request.user.is_authenticated or not request.user.has_perm('app0_access.view_security'):
        return redirect('%s?next=%s' % (settings.LOGIN_URL, request.path))
    if request.user.is_superuser:
        return redirect('/admin/')
    if not request.session.get('client'):  # adress is not selected
        return redirect('select location')
    client = Client.objects.get(pk=request.session['client'])
    alert = Alert.objects.filter(active=True, client=client.id)
    if len(alert) != 0:
        return redirect(reverse('warning', args=[0, alert.last().key]))
    d_action = request.POST.get('d_action')
    if d_action == 'start':
        try:
            process(client.key).kill()
        except AttributeError:
            pass
        if settings.DEBUG:
            with open(os.path.join(settings.BASE_DIR, 'process_alert_' + client.key + '.log'), 'w') as loga:
                Popen([settings.PYTHON, os.path.join(settings.BASE_DIR, 'app1_base/process_alert.py'), client.key],
                      stdout=loga, stderr=STDOUT)
        else:
            Popen([settings.PYTHON, os.path.join(settings.BASE_DIR, 'app1_base/process_alert.py'), client.key])
        client.change = True
        client.rec = True
        client.start_rec = timezone.now()
        client.save(update_fields=['change', 'rec', 'start_rec', ])
        Camera.objects.filter(client=client, active=True, active_automatic=True).update(change=True,
                                                                                        on_rec=True)
        time.sleep(2)
    if d_action == 'stop':
        try:
            process(client.key).kill()
        except AttributeError:
            pass
        client.change = True
        client.rec = False
        client.save(update_fields=['change', 'rec'])
        Camera.objects.filter(client=client, active=True, active_automatic=True).update(change=True, on_rec=False)
        time.sleep(2)
    context = {'url_for_index': '/', 'running': client.rec, 'client': client, 'connected': is_client_connected(client)}
    if process(client.key) is False and client.rec:
        context.update({'message': _('Alert not running, technical problem'), 'category': 'warning'})
    return render(request, 'app1_base/index.html', context)


def warning(request, first_alert, key):
    alert = Alert.objects.filter(active=True, key=key)
    if not alert:
        return redirect('/')
    else:
        client = alert.last().client
    alert = Alert.objects.filter(active=True, client=client.id).order_by('when')
    user_language = 'fr'
    translation.activate(user_language)
    action = request.POST.get('alert')
    if action == 'cancel':
        for a in alert:
            a.active = False
            a.save()
        return redirect('/')
    imgs_alert = Result.objects.filter(
        alert=True, camera__client=client.id).filter(
        time__gte=alert.first().when).order_by('-id')[first_alert: first_alert + 9]
    img_alert_array = [imgs_alert[i: i + 3] for i in range(0, len(imgs_alert), 3)]
    context = {'first_alert': first_alert, 'img_alert_array': img_alert_array, 'key': key, 'client': client}
    return render(request, 'app1_base/warning.html', context)


def stop_camera(client, token_stop_s):
    log_views.warning(f'Starting stop camera')
    time.sleep(settings.TIME_ON_CAMERA)
    log_views.warning(f'end of sleeping')
    client_objects = Client.objects.get(pk=client)
    if client_objects.stop_thread == token_stop_s:
        client_objects.change = True
        client_objects.save(update_fields=['change', ])
        Camera.objects.filter(active=True, active_automatic=True, client=client).update(on_camera_LD=False,
                                                                                        on_camera_HD=False, change=True)
        log_views.warning(f'token stop have been check')


@login_required
@permission_required('app0_access.view_security')
def camera(request):
    if 'log_views' not in globals():
        global log_views
        log_views = Logger('views', level=logging.ERROR).run()
    token_stop = secrets.token_hex()
    log_views.warning(f'token stop is   {token_stop}')
    camera_v = Camera.objects.filter(active=True, active_automatic=True, client=request.session['client'])
    camera_v.update(on_camera_LD=True, change=True)
    client_v = Client.objects.filter(pk=request.session['client'])
    client_v.update(change=True, stop_thread=token_stop)
    thread = Thread(target=stop_camera, args=[request.session['client'], token_stop])
    thread.start()
    list_cam = []
    for cam in camera_v:
        camera_uri = CameraUri.objects.filter(camera=cam, use=True).first()
        log_views.info(f'getting the use uri   {camera_uri}')
        if not camera_uri:
            camera_uri = CameraUri.objects.filter(camera=cam).last()
            log_views.info(f'getting the default uri   {camera_uri}')
        list_cam.append((cam, camera_uri))
    log_views.info(f'Camera list_cam   {list_cam}')
    camera_array = [list_cam[i: i + 3] for i in range(0, len(list_cam), 3)]
    log_views.info(f'Camera array   {camera_array}')
    archive_form = ArchiveForm(request)
    connected = is_client_connected(client_v[0])
    context = {
        'refresh': settings.TIME_ON_CAMERA, 'client': client_v[0], 'archive_form': archive_form,
        'camera': camera_array, 'info': {'version': settings.VERSION, }, 'connected': connected,
        'url_for_index': '/', 'logo_client': client_v[0].logo_perso}
    if not connected:
        if settings.DOMAIN == 'serenicia':
            context.update({'message': _(
                'Your Serenicia box is not connected, you can not see the video'), 'category': 'warning'})
        if settings.DOMAIN == 'Protecia':
            context.update({'message': _(
                'Your Protecia box is not connected, you can not see the video'), 'category': 'warning'})

    return render(request, 'app1_base/camera.html', context)


@login_required
@permission_required('app0_access.view_security')
def archive(request):
    if 'log_views' not in globals():
        global log_views
        log_views = Logger('views', level=logging.ERROR).run()
    # camera_v = Camera.objects.filter(active=True, active_automatic=True, client=request.session['client'])
    client_v = Client.objects.filter(pk=request.session['client'])
    archive_form = ArchiveForm(request)
    connected = is_client_connected(client_v[0])
    context = {
        'client': client_v[0], 'archive_form': archive_form, 'connected': connected, 'url_for_index': '/',
        'logo_client': client_v[0].logo_perso}
    if not connected:
        if settings.DOMAIN == 'serenicia':
            context.update({'message': _(
                'Your Serenicia box is not connected, you can not see the video'), 'category': 'warning'})
        if settings.DOMAIN == 'Protecia':
            context.update({'message': _(
                'Your Protecia box is not connected, you can not see the video'), 'category': 'warning'})
    return render(request, 'app1_base/archive.html', context)


@login_required
@permission_required('app0_access.view_security')
def last(request, cam):
    token_stop = secrets.token_hex()
    camera = Camera.objects.get(pk=cam, active=True, client=request.session['client'])
    camera.on_camera_HD = True
    camera.change = True
    camera.save(update_fields=['change', 'on_camera_HD', ])
    Client.objects.filter(pk=request.session['client']).update(change=True, stop_thread=token_stop)
    thread = Thread(target=stop_camera, args=[request.session['client'], token_stop])
    thread.start()
    time.sleep(2)
    domain = settings.DOMAIN
    # path_img_box = os.path.join(settings.MEDIA_URL, client.last().folder, 'temp_img_cam_'+str(cam)+'.jpg')
    return render(request, 'app1_base/last_img.html', {'cam': camera, 'domain': domain})


@login_required
@permission_required('app0_access.view_security')
def panel(request, first, alert, correction=0):
    client = Client.objects.get(pk=request.session['client'])
    if request.method == 'POST':
        first = 0
        action_form = request.POST.get("valid_filter", "")
        if action_form == 'ok':
            stuffs = request.POST.get("stuffs_char_foreign", "")
            if stuffs:
                request.session['class_nb'] = int(stuffs)
            else:
                request.session['class_nb'] = -1
        else:
            request.session['class_nb'] = -1
    filter_class = AlertStuffsChoice.objects.filter(pk=request.session.get("class_nb", -1))
    if filter_class:
        filter_class = filter_class[0].stuffs
    else:
        filter_class = 'all'

    # Case there is no result
    if not Result.objects.filter(camera__client=request.session['client']):
        form = FilterForm(client=request.session['client'])
        context = {'class': filter_class, 'form': form, 'first': first,
                   'first_alert': first, 'img_array': [], 'client': client,
                   'correction': correction, 'alert': alert}
        return render(request, 'app1_base/panel.html', context)

    # Main request
    img_main = Result.objects.filter(camera__client=request.session['client'], alert=alert)
    if correction == 0:
        img_main = img_main.filter(force_send=False)
    elif correction == 1:
        img_main = img_main.filter(correction=True)
    elif correction == 2:
        img_main = img_main.filter(force_send=True)
    elif correction == 3:
        import app1_base.dataset as dt
        img_main = dt.certain(filter_class)
    if filter_class == "all":
        imgs = img_main.order_by('-id')[first: first + 12]
    else:
        imgs = img_main.filter(
            object__result_object__contains=filter_class).order_by('-id').annotate(
            c=Count('object__result_object'))[first: first + 12]
    img_array = [imgs[i: i + 3] for i in range(0, len(imgs), 3)]
    form = FilterForm(client=request.session['client'])
    context = {'class': filter_class, 'form': form, 'first': first,
               'correction': correction, 'img_array': img_array, 'client': client, 'alert': alert}
    if not is_client_connected(client):
        if settings.DOMAIN == 'serenicia':
            context.update({'message': _(
                'Your Serenicia box is not connected, you can not see the video'), 'category': 'warning'})
        if settings.DOMAIN == 'Protecia':
            context.update({'message': _(
                'Your Protecia box is not connected, you can not see the video'), 'category': 'warning'})
    return render(request, 'app1_base/panel.html', context)


@login_required
@permission_required('app0_access.view_security')
def panel_detail(request, id, box=0):
    result = Result.objects.get(id=id, camera__client=request.session['client'])
    if box == 1:
        no_box = result.file.split('.')[0] + '_no_box.jpg'
    elif box == 2:
        return HttpResponse(result.brut)
    elif box == 3:
        img_pil = Image.open(settings.MEDIA_ROOT + '/' + result.file.split('.')[0] + '_no_box.jpg')
        draw = ImageDraw.Draw(img_pil)
        result_list = json.loads(result.brut.replace("'", '"'))
        y = 0
        for r in result_list:
            outline = "green"
            if float(r[1]) < result.camera.threshold: outline = "red"
            box = ((int((r[2][0] - (r[2][2] / 2))),
                    int((r[2][1] - (r[2][3] / 2)))),
                   (int((r[2][0] + (r[2][2] / 2))),
                    int((r[2][1] + (r[2][3] / 2)))))
            draw.rectangle(box, outline=outline, width=int(3))
            draw.text((box[0][0], box[0][1] + (y * 20)), r[0] + "(" + str(r[1])[: 4] + ")", fill=outline,
                      font=ImageFont.truetype(
                          "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", int(30)))
            y += 1
        response = HttpResponse(content_type='image/jpg')
        img_pil.save(response, 'JPEG')
        return response
    else:
        no_box = False
    return render(request, 'app1_base/panel_detail.html', {'img': result, 'id': id, 'no_box': no_box, })


@login_required
@permission_required('app0_access.view_security')
def get_video_token(request, result=None, get_back=None, first=None):
    client = Client.objects.get(pk=request.session['client'])
    token = client.token_video
    key_sha = hashlib.sha256(client.key.encode()).hexdigest()
    dom = request.META['HTTP_HOST']

    # retrocompatibility with client < 2.1
    if client.machine_id.docker_version >= 2.1:
        extra_url = '&key=' + key_sha
        port = str(int(client.machine_id.tunnel_port) + 1000)
    else:
        extra_url = ''
        port = str(int(client.tunnel_port) + 1000)

    if request.method == 'POST':
        hour = request.POST.get("hour", "")
        cam = request.POST.get("camera", "")
        minute = ("0" + request.POST.get("minute", ""))[-2:]
        return redirect(
            'http://' + dom.split(':')[0] + ':' + port + '/video?v=secu.backup_' +
            hour + ':' + minute + '_cam' + cam + '&l=' + dom + '_archive&token=' + token + extra_url)
    else:
        result = Result.objects.get(pk=result)
        date = result.video_time.strftime('%d:%m:%H:%M')
        return_url = '_panel_detection_' + first + '_' + get_back + '_0'
        return redirect('http://' + dom.split(':')[0] + ':' + port + '/video?v=secu.backup_' + date +
                        '_cam' + str(result.camera.id) + '&l=' + dom + return_url + '&token=' + token + extra_url)


def warning_detail(request, id, key):
    alert = Alert.objects.filter(active=True, key=key).order_by('when')
    alert = alert.first()
    if not alert:
        return redirect('/')
    else:
        client = alert.client
    try:
        img = Result.objects.get(id=id, camera__client=client)
    except Result.DoesNotExist:
        return redirect('/')
    imgs_alert = Result.objects.filter(alert=True).filter(time__gte=alert.when)
    ids = [i.id for i in imgs_alert]
    if id in ids:
        return render(request, 'app1_base/panel_detail.html', {'img': img, 'id': id})
    else:
        return redirect('/')


@login_required
@permission_required('app0_access.view_security')
def alert(request, suppr=False, pk=-1):
    client = Client.objects.get(pk=request.session['client'])
    alert_type = Alert_type.objects.filter(client=request.session['client'])
    autorization = dict(
        [(a[0], True) if a[0] in [a.allowed for a in alert_type] else (a[0], False) for a in ALERT_CHOICES])
    # if this is a POST request we need to process the form data
    if request.method == 'POST':
        typeForm = request.POST.get("type", "")
        # create a form instance and populate it with data from the request:
        if typeForm == "alert":
            form = AlertForm(request.POST, client=request.session['client'])
            # check whether it's valid:
            if form.is_valid():
                try:
                    alert_form = form.save(commit=False)
                    alert_form.client = Client.objects.get(pk=request.session['client'])
                    alert_form.save()
                    form.save_m2m()
                except IntegrityError:
                    pass
                return HttpResponseRedirect(reverse('alert'))
            else:
                aform = AutomatForm()
        elif typeForm == "auto":
            form = AutomatForm(request.POST)
            # check whether it's valid:
            if form.is_valid():
                # process the data in form.cleaned_data as required
                d = form.cleaned_data['day']
                h = form.cleaned_data['hour']
                m = form.cleaned_data['minute']
                a = form.cleaned_data['action']
                cron = CronTab(user=True)
                cmd = settings.PYTHON + ' ' + os.path.join(settings.BASE_DIR,
                                                           'app1_base/_running.py ' + a + ' ' + client.folder)
                job = cron.new(command=cmd, comment=secrets.token_hex())
                if d != '*':
                    h, m, d = local_to_utc(int(h), int(m), pytz.timezone(settings.TIME_ZONE), d=int(d))
                    job.dow.on(d)
                else:
                    h, m, _ = local_to_utc(int(h), int(m), pytz.timezone(settings.TIME_ZONE))
                job.minute.on(m)
                job.hour.on(h)
                cron.write()
                # redirect to a new URL:
                return HttpResponseRedirect('/alert/')
            else:
                form = AlertForm(client=request.session['client'])
    # if a GET (or any other method) we'll create a blank form
    else:
        form = AlertForm(client=request.session['client'])
        aform = AutomatForm()
    # suppr things
    if suppr == 'alert':
        Alert.objects.get(pk=int(pk), client=request.session['client']).delete()
    elif suppr == 'auto':
        cron = CronTab(user=True)
        cron.remove_all(comment=pk)
        cron.write()
    elif suppr == 'telegram':
        Telegram.objects.get(pk=int(pk), profile=request.user.profile.id).delete()

    # get all the alert and all the automatism
    alert = Alert.objects.filter(client=request.session['client'])
    cron = CronTab(user=True)
    auto = [utc_to_local(c.hour.render(), c.minute.render(), pytz.timezone(settings.TIME_ZONE),
                         c.dow.render()) + (c.command.split()[2], c.comment) for c in cron if
            client.folder in c.command]
    # test the telegram token
    telegram_token = Profile.objects.get(user=request.user).telegram_token
    chat_id = Telegram.objects.filter(profile=request.user.profile.id)
    if len(chat_id) == 0:
        chat_id = None

    # auto = [(a[0], a[1], DAY_CODE_STR[a[4]], a[-1]) for a in auto]
    return render(request, 'app1_base/alert.html', {
        'message': form.non_field_errors, 'category': 'warning', 'form': form,
        'alert': alert, 'aform': aform, 'auto': auto, 'autorization': autorization,
        'client': client, 'telegram_token': telegram_token, 'chat_id': chat_id})


@login_required
@permission_required('app0_access.view_security')
def get_last_analyse_img(request, cam_id):
    client = Client.objects.get(pk=request.session['client'])
    path_img_box = os.path.join(settings.MEDIA_ROOT, client.folder, 'temp_img_cam_' + str(cam_id) + '.jpg')
    try:
        age = time.time() - os.path.getmtime(path_img_box)
    except FileNotFoundError:
        path_img_broken = os.path.join(settings.STATIC_ROOT, 'app1_base', 'img', 'image-not-found.jpg')
        image_data = open(path_img_broken, "rb").read()
        return HttpResponse(image_data, content_type="image/jpg")
    if age > 60:
        path_img_wait = os.path.join(settings.STATIC_ROOT, 'app1_base', 'img', 'gifwait.gif')
        image_data = open(path_img_wait, "rb").read()
        return HttpResponse(image_data, content_type="image/gif")
    # cam = Camera.objects.get(id=cam_id)
    while True:
        try:
            im = Image.open(path_img_box)
        except OSError:
            continue
        response = HttpResponse(content_type='image/jpg')
        try:
            im.save(response, 'JPEG')
            break
        except OSError:
            continue
    return response


def thumbnail(request, im, key, w, h):
    if not request.user.is_authenticated:
        try:
            client = Alert.objects.filter(active=True, key=key).last().client.id
        except AttributeError:
            return None
    else:
        client = request.session['client']
        log_views.info(f'client is {client}')
    try:
        path_im = Result.objects.get(pk=im, camera__client=client).file
        path_im = os.path.join(settings.MEDIA_ROOT, path_im)
        im = Image.open(path_im)
    except (OSError, Result.DoesNotExist):
        path_img_broken = os.path.join(settings.STATIC_ROOT, 'app1_base', 'img', 'image-not-found.jpg')
        im = Image.open(path_img_broken)
        pass
    response = HttpResponse(content_type='image/jpg')
    im.thumbnail((w, h), Image.ANTIALIAS)
    im.save(response, 'JPEG')
    return response


def send_welcome_mail(request, user):
    pass


def reboot(request, profile):
    if request.user.is_superuser:
        client = Profile.objects.get(pk=profile).client
    else:
        client = Client.objects.get(pk=request.session['client'])
    client.reboot = True
    client.change = True
    client.save(update_fields=['change', 'reboot', ])
    return redirect('/')


@login_required
def select_client(request):
    try:
        request.session.pop('resident_id')
    except KeyError:
        pass
    if request.POST.get('client'):
        request.session['client'] = request.POST.get('client')
        return redirect('app1_base index')
    listclients = request.user.profilesecurity.client.all().order_by('cp', 'adress', 'room_number')
    # better to check if the camera is connected by timestamps
    is_connected = ['bg-lightblue' if timezone.now() - c.timestamp < timedelta(seconds=30) else 'bg-danger'
                    for c in listclients]
    nb_cam = [Camera.objects.filter(client=c, active=True, active_automatic=True).count() for c in listclients]
    nb_cam_lost = [Camera.objects.filter(client=c, active=True, active_automatic=False).count() for c in listclients]
    list_clients_connected = zip(listclients, is_connected, nb_cam, nb_cam_lost)
    display_adress = request.user.profile.display_adress
    return render(request, 'app1_base/client_selection.html', {'listclients': list_clients_connected,
                                                          'display_adress': display_adress})


def check_event(query, event_type, inactivity_time):
    event_display = {'person': _('Person'), 'cat': _('Cat'), 'dog': _('Dog'), 'car': _('Car')}
    events = []
    for ev in event_type:
        if query.filter(object__result_object=ev).count():
            previous = query.filter(object__result_object=ev).first()
            first_detect = previous
            for result in query.filter(object__result_object=ev):
                if not first_detect:
                    first_detect = result
                if (previous.time + timedelta(minutes=inactivity_time)) <= result.time:
                    events.append({'start': first_detect, 'end': previous, 'type': event_display[ev]})
                    first_detect = None
                previous = result
    return events


@login_required
def timeline(request):
    # TODO insérer gestion configuration depuis admin : temps d'inactivité
    event_type = ['person', 'car', 'cat', 'dog']
    inactivity_time = 2
    client = Client.objects.get(pk=request.session['client'])
    last_result = Result.objects.filter(object__result_object__in=event_type, camera__client=client).last()
    results = []
    for cam in Camera.objects.filter(client=client):
        query = Result.objects.filter(camera=cam, object__result_object__in=event_type,
                                      time__date=last_result.time.date()).order_by('time')
        list_event = check_event(query, event_type, inactivity_time)
        if list_event:
            results.extend(list_event)
    return render(request, 'app1_base/timeline.html',
                  {'results': sorted(results, key=lambda d: d['start'].time), 'client': client})


@login_required
def set_preferences(request):
    try:
        request.session.pop('resident_id')
    except KeyError:
        pass
    connected_user = User.objects.get(pk=request.user.id)
    context = {}
    if "serenicia" in settings.DOMAIN.lower():
        current_prefs_j = PreferencesSerenicia.objects.get_or_create(profile=connected_user.profile)[0]
        current_prefs = Preferences.objects.get_or_create(profile=connected_user.profile)[0]
        if request.method == 'POST':
            form_j = PreferencesSereniciaForm(request.POST, instance=current_prefs_j)
            form = PreferencesForm(request.POST, instance=current_prefs)
            if form_j.is_valid() and form.is_valid():
                current_prefs = form.save()
                current_prefs_j = form_j.save()
                context.update({'message': _('The modifications has been saved'), 'category': _('Saved')})
        context.update({'prefs': PreferencesForm(instance=current_prefs),
                        'prefs_j': PreferencesSereniciaForm(instance=current_prefs_j)})
        if connected_user.has_perm('app0_access.view_family'):
            resident_profile = None
            if request.session.get('res_id'):
                resident_profile = Profile.objects.get(user__pk=request.session['res_id'])
            elif connected_user.profileserenicia.user_list.count() == 1:
                resident_profile = connected_user.profileserenicia.user_list.get()
            if resident_profile:
                try:
                    resident_pref = PreferencesSerenicia.objects.get(profile=resident_profile)
                    for choice in PreferencesSerenicia.INTERVENTIONS_CHOICES:
                        if choice[0] == resident_pref.interventions:
                            context['interventions_force_display'] = choice[1]
                except ObjectDoesNotExist:
                    pass
    else:
        current_prefs = Preferences.objects.get_or_create(profile=connected_user.profile)[0]
        if request.method == 'POST':
            form = PreferencesForm(request.POST, instance=current_prefs)
            if form.is_valid():
                current_prefs = form.save()
                context.update({'message': _('The modifications has been registered'), 'category': _('Saved')})
        context['prefs'] = PreferencesForm(instance=current_prefs)
    return render(request, 'app4_ehpad_base/preferences.html', context)
