# -*- coding: utf-8 -*-
"""
Created on Sun Apr 14 21:29:53 2019

@author: julien
"""
import json
import secrets
import time
from math import ceil
from random import choice
from urllib.parse import quote_plus

import pytz
import requests
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required, permission_required
from django.core import serializers
from django.core.exceptions import ObjectDoesNotExist
from django.core.files.storage import default_storage
from django.db.models.functions import Lower
from django.forms import model_to_dict
from django.template.defaultfilters import pluralize
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt

import app4_ehpad_base.views2
import app4_ehpad_base.views_calendar as vc
from django.conf import settings
from django.shortcuts import render, redirect
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from django.http import HttpResponseRedirect, HttpResponse, JsonResponse, HttpResponseServerError

from app10_social_activities.views import get_social_life_data
from app6_care.models import Intervention, InterventionDetail, FreeComment
from app15_calendar.models import PlanningEvent
from app15_calendar.views import calendar_configuration, get_birthday_events
from .api_netsoins import TLSAdapter, get_netsoins_url_get
from .forms import SectorSelector, PhotoForm, Sector2Selector, NewAccount, UploadPhotos, PhotoFromStaff, PublicPhoto, \
    PhotoFromStaffSensitive, EmptyRoomCleanedForm
from django.utils import translation, timezone
from app1_base.models import Result, SubSector, Profile, Client
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _

from .models import Pic, MealBooking, ProfileSerenicia, Card, MenuEvaluation, UserListIntermediate, BlogPost, \
    WordToRecord, IntonationToRecord, PreferencesSerenicia, EmptyRoomCleaned
import glob

from app4_ehpad_base.views_administrative_documents import progress_bar
from app4_ehpad_base.views_cuisine_eval import display_meal, reservation

from pathlib import Path
from PIL import Image
import logging
from app1_base.log import Logger


def print_timer(last, text):
    print(f"{text}: {round(time.time() - last, 3)}")


def public_photo_form(request):
    if request.FILES.get('file'):
        form_photo_public = PublicPhoto(request.POST, request.FILES)
        if form_photo_public.is_valid():
            added_photo = form_photo_public.save()
            added_photo.added_by = User.objects.get(id=request.user.id)
            added_photo.save()
            request.session['public_photo_success'] = True
    if request.META.get('HTTP_REFERER'):
        return redirect(request.META.get('HTTP_REFERER'))
    return redirect('app4_ehpad_base index')


def get_data_modal_booking(user, selected_resident):
    if user.has_perm('app0_access.view_family'):
        is_family = True
        user_guests = User.objects.filter(profileserenicia__user_list__user=selected_resident,
                                          groups__permissions__codename='view_family').exclude(id=user.id)
        bookinglist = MealBooking.objects.order_by('date').filter(date__gte=datetime.now().date(), guests__pk=user.id)
    else:
        is_family = False
        user_guests = []
        bookinglist = []
    return {'user_guests': user_guests, 'is_family': is_family, 'bookinglist': bookinglist,
            'today': datetime.now().date().strftime('%d/%m/%Y')}


def get_data_photo_album(folder):
    result = []
    list_index = 0
    elem_to_first_place = None
    for album in Path(settings.MEDIA_ROOT + '/residents/' + folder + '/photo_family/').glob('*'):
        tmp_data = {'name': album.name, 'thumbnail_url': None}
        for elem in album.iterdir():
            if elem.is_dir():
                for thumb in elem.iterdir():
                    tmp_data[
                        'thumbnail_url'] = settings.MEDIA_URL + 'residents/' + folder + '/photo_family/' + album.name + '/thumb/' + thumb.name
                break
        if not tmp_data['thumbnail_url']:
            elem_to_first_place = list_index
            tmp_data['thumbnail_url'] = settings.STATIC_URL + 'app4_ehpad_base/img/dossier_photos_200x166.png'
        result.append(tmp_data)
        list_index += 1
    result = sorted(result, key=lambda x: x['thumbnail_url'].split('/')[-1], reverse=True)
    if elem_to_first_place:
        result.insert(0, result.pop(result.index(elem_to_first_place)))
    if len(result) > 0:
        return result
    else:
        return None


def goto_page(page, user_language=None):
    response = redirect(page)
    response.set_cookie(settings.LANGUAGE_COOKIE_NAME, user_language)
    return response


def index(request):
    if 'log_app4_ehpad_base' not in globals():
        global log_app4_ehpad_base
        log_app4_ehpad_base = Logger('app4_ehpad_base', level=logging.ERROR).run()
    log_app4_ehpad_base.debug(f"le language est :{request.LANGUAGE_CODE} \n")
    # request.session['django_timezone'] = 'Europe/Paris'
    if not request.user.is_authenticated:
        return redirect('%s?next=%s' % (settings.LOGIN_URL, request.path))
    timezone.activate(settings.TIME_ZONE)
    connected_user = User.objects.prefetch_related('profileserenicia',
                                                   'profileserenicia__user_list').get(pk=request.user.id)
    # use the language of the user
    if hasattr(connected_user, 'profile'):
        user_language = connected_user.profile.language
    else:
        user_language = None

    # request.session[translation.LANGUAGE_SESSION_KEY] = user_language
    if connected_user.is_superuser:
        return goto_page('/admin/')
    elif connected_user.profileserenicia.homepage == 'cuisine':
        return goto_page('Cuisine index', user_language=user_language)
    elif connected_user.has_perm('app0_access.view_residentehpad') or connected_user.has_perm('app0_access.view_residentrss'):
        return goto_page('app13_resident index', user_language=user_language)
    linked_resident_profile = connected_user.profileserenicia.user_list.count()
    if linked_resident_profile > 1 or connected_user.has_perm('app0_access.view_care'):
        # the user got multiple affected resident and don't have selected one yet
        return goto_page('select resident', user_language=user_language)
    if linked_resident_profile == 1:
        # the user got only one affected resident
        request.session['resident_id'] = connected_user.profileserenicia.user_list.get().user.id
        return goto_page('personal page', user_language=user_language)
    elif linked_resident_profile < 1:
        # no assigned resident to the connected user
        return goto_page('welcome', user_language=user_language)
    return redirect('/accounts/logout/')


def create_ref(resident, access):
    ref_temp = ProfileSerenicia.objects.filter(user__groups__permissions__codename=access,
                                               user_list=resident.profile)
    ref_temp = ref_temp.exclude(user__last_login__isnull=True).exclude(user__is_active=False)
    return [ref.user for ref in ref_temp]


def get_thumbnail_pic(pic_url):
    pic_name = pic_url.split('/')[-1]
    insert_index = pic_url.find(pic_name)
    return f'{pic_url[:insert_index]}thumbnails/{pic_name}'


def get_filtered_interventions(resident, connected_user):
    if connected_user.has_perm('app0_access.view_family'):
        try:
            level = PreferencesSerenicia.objects.get(profile=resident.profile).interventions
        except ObjectDoesNotExist:
            level = PreferencesSerenicia.objects.get_or_create(profile=connected_user.profile)[0].interventions
    else:
        level = PreferencesSerenicia.objects.get_or_create(profile=connected_user.profile)[0].interventions
    if level:
        interventions = get_last_12_interventions(resident)
    else:
        interventions = None
    return {'last_12_interventions': interventions, 'interventions_lvl': level}


def personal_page(request):
    blog_articles = BlogPost.objects.all().order_by('-created_on')[:6]
    if not request.session.get('resident_id'):
        return redirect('app4_ehpad_base index')
    message = {}
    if request.FILES.get('photo_from_staff'):
        form_photo = PhotoFromStaff(request.POST, request.FILES)
        if form_photo.is_valid():
            form_photo.save()
            message = {'message': _('Photo successfully sent !'), 'category': _('Private photo')}
    elif request.FILES.get('photo_sensitive'):
        form_photo = PhotoFromStaffSensitive(request.POST, request.FILES)
        if form_photo.is_valid():
            form_photo.save()
            message = {'message': _('Photo successfully sent !'), 'category': _('Sensitive photo')}
    ws_alexa = 'wss://' + request.get_host() + ':' + request.META.get('SERVER_PORT') + '/ws_alexa/'
    connected_user = User.objects.get(id=request.user.id)
    resident = User.objects.select_related('profileserenicia').get(pk=request.session['resident_id'])
    civility = _(resident.profile.civility)
    firstname = _(resident.first_name[0])
    lastname = _(resident.last_name)
    carousel_images = show_images(resident.profileserenicia.folder)
    carousel_active_pic = None
    if request.method == 'POST':
        if request.POST.get('booking_date'):
            message = reservation(request)
        elif request.POST.get('pic_url'):
            carousel_active_pic = get_thumbnail_pic(request.POST.get('pic_url'))
    else:
        try:
            carousel_active_pic = carousel_images['images'][0]['image']
        except (KeyError, IndexError):
            pass
    communication = app4_ehpad_base.views2.index_comgeneral(request)
    new_event, calendar_message = vc.update_planning(request)
    event_data = vc.display_planning(request)
    meal_data = display_meal(resident.id)
    ref_as = create_ref(resident, "view_as")
    ref_ash = create_ref(resident, "view_ash")
    ref_ide = create_ref(resident, "view_ide")
    profile_pic = get_profile_pic_url(resident)
    data_modal_booking = get_data_modal_booking(connected_user, resident.id)
    show_com = True
    for groups in connected_user.groups.all():
        if groups.name == 'Famille':
            show_com = False
    comment_of_the_week = get_comment_of_the_week(resident.id, show_com)
    main_resident_informations = get_main_resident_informations(resident.id)
    photo_album = get_data_photo_album(resident.profileserenicia.folder)
    social_life_data = get_social_life_data(resident.profileserenicia)
    bar_progress = progress_bar(request)
    family_list = User.objects.filter(profileserenicia__user_list__user=resident,
                                      groups__permissions__codename='view_family')

    # GET doctor and kine of resident
    practicians_list = []
    dr = User.objects.filter(groups__permissions__codename='view_practicians')
    for doc in dr:
        if resident.profile in doc.profileserenicia.user_list.all():
            practicians_list.append(doc)

    if not message:
        message = calendar_message
    contexte = {'url_for_index': '/', 'new_event': new_event, 'communication': communication,
                'data_modal_booking': data_modal_booking,
                'main_resident_informations': main_resident_informations,
                'ws_alexa': ws_alexa, 'profile_pic': profile_pic, "ref_as": ref_as, "ref_ash": ref_ash,
                "ref_ide": ref_ide, "blog": blog_articles, 'social_life_data': social_life_data,
                'bar_progress': bar_progress, 'carousel_active_pic': carousel_active_pic, 'family_list': family_list,
                'praticiens': practicians_list, 'comment_of_the_week': comment_of_the_week, 'civility': civility,
                'firstname': firstname,
                'lastname': lastname,
                'calendar': calendar_configuration(display='month',
                                                   events=PlanningEvent.objects.filter(
                                                       participants=resident.profileserenicia))}
    contexte['calendar']['events'].extend(list(get_birthday_events(resident.profileserenicia,
                                                                   connected_user.profileserenicia)))
    contexte.update(get_filtered_interventions(resident, connected_user))
    if photo_album:
        contexte['photo_album'] = photo_album[:5]
    if connected_user.has_perm('app0_access.view_photostaff'):
        contexte['form_photo'] = PhotoFromStaff(initial={'folder': resident.profileserenicia.folder})
        contexte['form_photo_sensitive'] = PhotoFromStaffSensitive(initial={'folder': resident.profileserenicia.folder})
    context = {**event_data, **contexte, **meal_data, **carousel_images, **message}
    return render(request, 'app4_ehpad_base/index.html', context)


@login_required
@permission_required('app0_access.view_createaccount')
def create_account(request):
    context = {}
    if request.method == 'POST':
        form = NewAccount(request.POST)
        if form.is_valid():
            user, is_created = form.save()
            if is_created:
                context['created_user'] = user
            else:
                context['error'] = True
    else:
        form = NewAccount({'created_by': request.user})
    context['form'] = form
    return render(request, 'app4_ehpad_base/create_account.html', context)


@login_required
def welcome(request):
    return render(request, 'app4_ehpad_base/welcome.html')


def get_formatted_date(start, end):
    delta = relativedelta(start, end)
    years, months, days = '', '', ''
    if delta.years > 0:
        years = str(delta.years)
        years += ' ' + _('year{}').format(pluralize(delta.years)) + ' '
    if delta.months > 0:
        months = str(delta.months)
        months += ' ' + _('month{}').format(pluralize(delta.months)) + ' '
    if delta.days > 0 and not months and not years:
        days = str(delta.days)
        days += ' ' + _('day{}').format(pluralize(delta.days))
    return years + months + days


def is_birthday(birth_date):
    if birth_date.day == datetime.now().day and birth_date.month == datetime.now().month:
        return True
    return False


def get_eval_data(resident):
    result = {'vote_count': MenuEvaluation.objects.filter(voter=resident.user, menu__date__lte=datetime.now().date(),
                                                          menu__date__gte=(datetime.now().date() - timedelta(
                                                              days=7))).count(),
              'badge_color': 'bg-lightblue'}
    tomorrow = datetime.now().date() + timedelta(days=1)
    vote_count_tomorrow = MenuEvaluation.objects.filter(voter=resident.user, menu__date__lte=tomorrow,
                                                        menu__date__gte=(tomorrow - timedelta(days=7))).count()
    if result['vote_count'] <= 3:
        result['badge_color'] = 'bg-danger'
    elif vote_count_tomorrow <= 3:
        result['badge_color'] = 'bg-warning'
    return result


def actualize_resident_in_session(session, user_resident):
    session['res_name'] = user_resident.last_name + " " + user_resident.first_name
    try:
        session['res_lastname'] = f'{user_resident.first_name[0]}. {user_resident.last_name}'
    except AttributeError:
        session['res_lastname'] = user_resident.last_name
    session['profile_pic'] = get_profile_pic_url(user_resident)
    session['resident_id'] = user_resident.id


def calculate_age(born):
    today = timezone.localdate()
    return today.year - born.year - ((today.month, today.day) < (born.month, born.day))


@login_required
def select_resident(request, form_filter=None, formsubsector=None, sub_sector_filter=None):
    # log_app4_ehpad_base.debug(f"le language2 est :{translation.get_language()} \n")
    # log_app4_ehpad_base.debug(f"le language3 est :{translation.get_language_from_request(request, check_path=False)} \n")
    # total = time.time()
    can_view_all = not request.user.has_perm('app0_access.view_family')
    if not can_view_all:
        room_filter = 'myresidents'
    else:
        room_filter = 'residents'
    if request.method == 'POST':
        if request.POST.get('res_id'):
            selected_resident = User.objects.get(pk=request.POST.get('res_id'))
            actualize_resident_in_session(request.session, selected_resident)
            return redirect('personal page')
        room_filter = request.POST.get('rooms')
        formsector = Sector2Selector(request.POST)
        if formsector.is_valid():
            form_filter = formsector.cleaned_data['filtersector']
        lensubsector = SubSector.objects.filter(sector=form_filter).count()
        if lensubsector > 1:
            formsubsector = SectorSelector(request.POST)
            if formsubsector.is_valid():
                sub_sector_filter = formsubsector.cleaned_data['filter']
            formsubsector.fields['filter'].queryset = SubSector.objects.filter(sector=form_filter)
        last_filter = {}
        if form_filter:
            last_filter['filtersector'] = form_filter.id
        if sub_sector_filter:
            last_filter['filter'] = sub_sector_filter.id
        request.session['last_filter'] = last_filter
    else:
        request.session['resident_id'] = None
        formsector = Sector2Selector()
        if request.session.get('last_filter') is not None:
            form_filter = request.session['last_filter'].get('filtersector')
            sub_sector_filter = request.session['last_filter'].get('filter')
            formsector = Sector2Selector(initial=request.session['last_filter'])
            lensubsector = SubSector.objects.filter(sector=form_filter).count()
            if lensubsector > 1:
                formsubsector = SectorSelector()
            if sub_sector_filter:
                formsubsector = SectorSelector(initial=request.session['last_filter'])
                formsubsector.fields['filter'].queryset = SubSector.objects.filter(sector=form_filter)
    room_list = Client.objects.all()
    if room_filter == 'residents':
        room_list = room_list.filter(profile__isnull=False)
    elif room_filter == 'emptyrooms':
        room_list = room_list.filter(profile__isnull=True)
    elif room_filter == 'myresidents':
        room_list = room_list.filter(profile__in=request.user.profileserenicia.user_list.all())
    elif room_filter == 'alerts':
        room_list = room_list.filter(alert__active=True)

    room_list = room_list.order_by(Lower('profile__user__last_name')).exclude(
        profile__user__profileserenicia__status='deceased')
    if form_filter:
        room_list = room_list.filter(sector__sector=form_filter)
        if sub_sector_filter:
            room_list = room_list.filter(sector=sub_sector_filter).order_by('room_number')
    else:
        formsubsector = None
    # last = time.time()
    result = []
    for room in room_list:
        try:
            tmp_user = ProfileSerenicia.objects.get(user__profile__client=room)
            user = {'resident': tmp_user,
                    'since_entry': get_formatted_date(timezone.localdate(), tmp_user.entry_date),
                    'eval_data': get_eval_data(tmp_user.user.profile),
                    }
            try:
                user['birthday'] = is_birthday(tmp_user.birth_date)
                user['age'] = calculate_age(tmp_user.birth_date)
            except AttributeError:
                pass
            try:
                user['profile_pic'] = tmp_user.user.profile.photo.url
            except ValueError:
                pass
        except ObjectDoesNotExist:
            user = {'empty': room,
                    'cleaned': EmptyRoomCleaned.objects.filter(client=room, inventory=True, disinfection=True,
                                                               painting=True, menage=True, bed=True).exists()
                    }
        result.append(user)

    # print_timer(last, 'ROOM FOR')
    # last = time.time()
    r = render(request, 'app4_ehpad_base/client_selection.html',
               {'residentlist': result, 'formsector': formsector, 'formsubsector': formsubsector,
                'can_view_all': can_view_all, 'option': room_filter, 'displaylist': list(room_list.values_list('id', flat=True))})
    # print_timer(last, 'RENDERING')
    # print_timer(total, 'TOTAL')
    return r


@login_required
def room_cleaned(request, room_id):
    # Gestion du form empty room cleaned
    try:
        roomclean = EmptyRoomCleaned.objects.get_or_create(client=Client.objects.get(id=room_id))[0]
    except ObjectDoesNotExist:
        return redirect('app4_ehpad_base index')
    if request.method == 'POST':
        formclean = EmptyRoomCleanedForm(request.POST)
        if formclean.is_valid():
            roomclean.inventory = formclean.cleaned_data.get('inventory')
            roomclean.disinfection = formclean.cleaned_data.get('disinfection')
            roomclean.painting = formclean.cleaned_data.get('painting')
            roomclean.menage = formclean.cleaned_data.get('menage')
            roomclean.bed = formclean.cleaned_data.get('bed')
            roomclean.save()
        return redirect('app4_ehpad_base index')
    formclean = EmptyRoomCleanedForm(instance=roomclean)

    return render(request, 'app4_ehpad_base/client_selection_empty_clean.html', {'clean': formclean})


@login_required
def get_videochat_url(request):
    """display a jitsi conference configured with the user name and the selected roomname"""
    username = request.user.first_name + " " + request.user.last_name
    ws_alexa = 'wss://' + request.get_host() + ':' + request.META.get('SERVER_PORT') + '/ws_alexa/'
    context = {'username': username, 'ws_alexa': ws_alexa}
    if 'contact' in request.get_full_path():
        if request.method == 'POST':
            contact_id = request.POST.get('selected')
            if request.user.has_perm('app0_access.view_contact'):
                user = User.objects.get(pk=contact_id)
                ProfileSerenicia.objects.get(user=request.user).user_waiting.remove(user)
            else:
                user = request.user
                ProfileSerenicia.objects.get(user__id=contact_id).user_waiting.add(user)
        context['roomname'] = 'contact.' + user.username + "." + str(user.profileserenicia.token_video_call)
    else:
        resident = User.objects.get(pk=request.session['resident_id'])  # resident identification
        context['roomname'] = resident.first_name.lower() + resident.last_name.lower() + str(
            resident.profileserenicia.token_video_call)
    return render(request, 'app4_ehpad_base/videochat.html', context)


@login_required
def presenceclient(request):
    """display list of client with their status in the room"""
    form_filter = None
    if request.method == 'POST':  # filter selected in list
        option = request.POST.get('orderby')  # order by filter
        form = SectorSelector(request.POST)
        if form.is_valid():
            form_filter = form.cleaned_data['filter']  # sector filter
    else:
        option = "0"
        form = SectorSelector()
    results = []
    # get list of last person detected for each camera
    listpersonlastdetection = Result.objects.order_by('camera', 'camera__client', '-time').filter(
        object__result_object='person').distinct('camera')
    # get list of last event for each camera
    listlastevent = Result.objects.order_by('camera', 'camera__client', '-time').distinct('camera')
    if form_filter is not None:  # check if a sector is selected
        listpersonlastdetection = listpersonlastdetection.filter(
            camera__client__clientsserenicia__sector=form_filter.id)
        listlastevent = listlastevent.filter(camera__client__clientsserenicia__sector=form_filter.id)
    lastclientchecked = {}
    list_person = []
    first_iter = True
    index_last_element = len(listlastevent) - 1

    if index_last_element < 0:  # check if list is not empty
        msg = str(_("No record available"))
        return HttpResponseRedirect('/error/' + msg)
    last_element = listlastevent[index_last_element]
    if listpersonlastdetection.count() != listlastevent.count():
        msg = str(_("No record available"))
        return HttpResponseRedirect('/error/' + msg)

    for (person, last) in zip(listpersonlastdetection, listlastevent):
        if not first_iter:  # no records in first iteration
            if lastclientchecked.camera.client.id != last.camera.client.id:  # change client
                if True in list_person:  # someone in the room
                    lastclientchecked.presence = True
                else:
                    lastclientchecked.presence = False
                if option == "0":
                    results.append(lastclientchecked)  # recording result
                if option == "1":
                    if lastclientchecked.presence:
                        results.append(lastclientchecked)  # recording result
                if option == "2":
                    if not lastclientchecked.presence:
                        results.append(lastclientchecked)  # recording result
                list_person = []
        if person.time == last.time:  # person on the camera
            list_person.append(True)
        lastclientchecked = last
        first_iter = False
    if last_element.camera.client.id == lastclientchecked.camera.client.id:  # recording last iteration
        if True in list_person:
            lastclientchecked.presence = True
        else:
            lastclientchecked.presence = False
        if option == "0":
            results.append(lastclientchecked)  # recording result
        if option == "1":
            if lastclientchecked.presence:
                results.append(lastclientchecked)  # recording result
        if option == "2":
            if not lastclientchecked.presence:
                results.append(lastclientchecked)  # recording result

    date_now = datetime.now()
    context = {"roomlist": results, "date": date_now.strftime("%d/%m/%Y, %H:%M:%S"), "option": option, 'form': form}
    return render(request, 'app4_ehpad_base/presence.html', context)


@login_required
def error_msg(request, msg):
    """"display the msg string to html page"""
    return render(request, 'app4_ehpad_base/error_message.html', {'msg': msg})


def get_profile_pic_url(user):
    try:
        url = user.profile.photo.url
        return url
    except (AttributeError, ValueError):
        return None


@login_required
def contact_selection(request):
    """display list of contact in relation with the resident"""
    result = None
    context = {}
    if 'contact' in request.get_full_path():
        if request.user.has_perm('app0_access.view_contact'):
            contact_list = request.user.profileserenicia.user_waiting.all()
        else:
            contact_list = User.objects.filter(groups__permissions__codename='view_contact')
        result = [{'user': user, 'group': 'sub_selection', 'contact': True} for user in contact_list]
        # for user in contact_list:
        #     tmp_contact = {'user': user, 'group': 'sub_selection', 'contact': True}
        #     result.append(tmp_contact)
    elif request.session.get('resident_id'):
        contact_list = User.objects.filter(profileserenicia__user_list__user=request.session['resident_id']).exclude(
            id=request.user.id)  # get a list of users in relation with the resident, exclude the connected user
        resident = User.objects.get(pk=request.session['resident_id'])
        result = [{'user': resident, 'group': 'top_selection', 'photo': get_profile_pic_url(resident)}]
        context['data_modal_booking'] = get_data_modal_booking(request.user, request.session['resident_id'])
        for user in contact_list:
            if user.has_perm('app0_access.view_family'):  # identifies the user's group
                tmp_contact = {'user': user, 'group': "sub_selection"}
                result.append(tmp_contact)
    if len(result) < 1:
        msg = str(_('No contact available.'))
        return HttpResponseRedirect('/error/' + msg)
    context['contactlist'] = result
    return render(request, 'app4_ehpad_base/contact_selection.html', context)


def show_images(folder, show_sensitive=False):
    # create path and url
    path = f'{settings.MEDIA_ROOT}/residents/{folder}'
    url = f'{settings.MEDIA_URL}residents/{folder}'
    # create list of dict with 2 url: thumbnail and full resolution for each existing pic in resident's folder path
    if show_sensitive:
        pictures = [{'image': f'{url}/thumbnails/{pic.name}', 'image_full': f'{url}/{pic.name}',
                     'sensitive': 'sensitive' in pic.name}
                    for pic in Path(path).glob('*') if not pic.is_dir()]
    else:
        pictures = [{'image': f'{url}/thumbnails/{pic.name}', 'image_full': f'{url}/{pic.name}'}
                    for pic in Path(path).glob('*') if not pic.is_dir() and 'sensitive' not in pic.name]
    # sort by date from most recent to oldest
    return {'images': sorted(pictures, key=lambda x: x['image'], reverse=True)}


def show_images_hd(folder):
    pics_location = settings.MEDIA_ROOT + '/residents/' + folder + '/*.jpg'
    list_pictures = [settings.MEDIA_URL + 'residents/' + folder + '/' + i.split('/')[-1] for i in
                     glob.glob(pics_location, recursive=False)]
    list_pictures.sort(reverse=True)
    carousel_images = {
        'images': list_pictures,
    }
    return carousel_images


@login_required
def photo_list(request, image_id=None):
    resident = User.objects.get(pk=request.session['resident_id'])
    images = show_images(resident.profileserenicia.folder)
    try:
        photos = Pic.objects.filter(profil__profile__user=request.user.id)
    except Exception as e:
        photos = Pic.objects.none()
    if request.method == 'POST':
        if request.POST.get('img_url'):
            form = PhotoForm(request.POST, request.FILES, request=request)
            if form.is_valid():
                form.save()
                return redirect('photo_list')
    else:
        form = PhotoForm(request=request)
    return render(request, 'app4_ehpad_base/photo_list.html',
                  {'form': form, 'photos': photos, 'images': images['images']})


@login_required
def access_gallery(request):
    context = {}
    profileserenicia = ProfileSerenicia.objects.get(user__pk=request.session['resident_id'])
    if request.method == 'POST':
        filename = request.POST.get('selected').split('thumbnails/')[-1]
        img_path = f'{settings.MEDIA_ROOT}/residents/{profileserenicia.folder}'
        if request.POST.get('delete'):
            Path(f'{img_path}/{filename}').unlink(missing_ok=True)
            Path(f'{img_path}/thumbnails/{filename}').unlink(missing_ok=True)
            context.update({'category': _('Deleting'), 'message': _('The photo was successfully deleted')})
        else:
            name = None
            if request.POST.get('sensitive'):
                name = filename.split('_')
                name.insert(1, 'sensitive')
                name = '_'.join(name)
            if request.POST.get('not-sensitive'):
                name = filename.replace('sensitive_', '')
            if name:
                Path(f'{img_path}/{filename}').rename(f'{img_path}/{name}')
                Path(f'{img_path}/thumbnails/{filename}').rename(f'{img_path}/thumbnails/{name}')
            context.update({'category': _('Saved'), 'message': _('Your modifications has been registered')})
    try:
        sensitive = PreferencesSerenicia.objects.get(profile=request.user.profile).sensitive_photos
    except ObjectDoesNotExist:
        sensitive = PreferencesSerenicia.sensitive_photos.field.default
    context['list_url'] = show_images(profileserenicia.folder, show_sensitive=sensitive).get('images')
    return render(request, 'app4_ehpad_base/gallery.html', context)


@login_required
def gallery_details(request):
    pic_url = request.POST.get('pic_url')
    if pic_url:
        return render(request, 'app4_ehpad_base/gallery_details.html', {'pic_url': pic_url, 'anchor': request.POST.get('anchor')})
    return redirect('Gallery')


def picto(picto):
    return settings.STATIC_URL + 'app4_ehpad_base/img/homemade_svg/' + picto + '_64x64.svg'


def get_last_12_interventions(selected_resident):
    data = []
    last_12_interventions = Intervention.objects.exclude(
        end=None, details__task_level_2__shared_with_family=False).filter(end__gte=timezone.now() - timedelta(
        days=7), patient=selected_resident).order_by('-end')[:12]

    for last_intervention in last_12_interventions:
        tasks = [
            {'name': task.task_level_2.name, 'pictogram': task.task_level_2.get_svg_path}
            for task in InterventionDetail.objects.filter(
                intervention=last_intervention).distinct('task_level_2')]
        # a ajouter pour améliorer : details__task_level_2__shared_with_family=False
        if tasks:
            short_tasks_list = [tasks[0]] if len(tasks) == 1 else [tasks[0], tasks[1]]

            try:
                nurse_avatar = last_intervention.nurse.profile.photo.url
            except ValueError:
                nurse_avatar = None

            data.append(
                {'date': last_intervention.end.astimezone(pytz.timezone(settings.TIME_ZONE)).strftime('%d/%m - %H:%M'),
                 'simplified_name': last_intervention.type.name,
                 'nurse': last_intervention.nurse,
                 'tasks': tasks,
                 'nurse_avatar': nurse_avatar,
                 'tasks_short_list': short_tasks_list,
                 'undisplayed_tasks': len(tasks) - len(short_tasks_list)})

    return data


def get_comment_of_the_week(selected_resident, show_com):
    if show_com:
        comment_of_the_week = FreeComment.objects.filter(patient=selected_resident,
                                                         start__gte=timezone.now() - timedelta(days=7)).order_by(
            '-start')[:6]
    else:
        comment_of_the_week = []
    return comment_of_the_week


def get_main_resident_informations(selected_resident):
    required_cards = len(Card.CARD_CHOICES)
    provided_cards = len(Card.objects.filter(user_resident=selected_resident))
    # civilité + nom + # chambre

    main_resident_informations = {
        'administrative_files_completeness': ceil(provided_cards / required_cards * 100),
        'got_multi_resistant_bacteria': ProfileSerenicia.objects.get(user=selected_resident).bacterium,
    }
    try:
        main_resident_informations['room_number'] = ProfileSerenicia.objects.get(
            user=selected_resident).user.profile.client.room_number
    except AttributeError:
        main_resident_informations['room_number'] = None
    return main_resident_informations


def handle_uploaded_file(file, dest_folder):
    file_dest = dest_folder + datetime.now().date().strftime('%d-%m-%Y') + file.name
    if Path(file_dest).exists():
        ext = file.name.split('.')[-1]
        file_dest = file_dest.replace('.' + ext, '')
        img_count = sum(1 for path in Path(dest_folder).glob('*') if path.is_file())
        file_dest = f'{file_dest}{img_count}.{ext}'
    with open(file_dest, 'wb+') as destination:
        for chunk in file.chunks():
            destination.write(chunk)


def create_thumbnail_album(img, dest_folder):
    dest_folder += 'thumb/'
    [thumb.unlink() for thumb in Path(dest_folder).glob('*thumbnail.*')]
    Path(dest_folder).mkdir(exist_ok=True)
    file_dest = dest_folder + datetime.now().date().strftime('%d-%m-%Y') + 'thumbnail.' + img.name.split('.')[-1]
    with open(file_dest, 'wb+') as destination:
        for chunk in img.chunks():
            destination.write(chunk)
    thumb = Image.open(file_dest)
    thumb.thumbnail((150, 150))
    thumb.save(file_dest)


@login_required
def photo_from_family(request, name=None):
    context = {}
    resident = ProfileSerenicia.objects.get(user__pk=request.session['resident_id'])
    base_dir = settings.MEDIA_ROOT + '/residents/' + resident.folder + '/photo_family/'
    if request.method == 'POST':
        new_name = request.POST.get('new_name')
        if new_name:
            new_dir = base_dir + new_name
            if Path(new_dir).exists():
                # already exist, go to existing or select new name
                context = {'exist': True, 'dir_name': new_name}
            else:
                # create new folder
                Path(new_dir).mkdir(parents=True)
                # redirect to the new folder interface
                return redirect('photo_from_family', name=new_name)
        else:
            # save uploaded pictures
            form = UploadPhotos(request.POST, request.FILES)
            if form.is_valid():
                dest_folder = base_dir + name + '/'
                for img in request.FILES.getlist('images'):
                    handle_uploaded_file(img, dest_folder)
                last_pic = request.FILES.getlist('images')[-1]
                create_thumbnail_album(last_pic, dest_folder)

    if not name:
        # user clicked on the new folder button
        context['new_dir'] = True
        context['photo_album'] = get_data_photo_album(resident.folder)
        if context.get('exist'):
            for album in context['photo_album']:
                if album['name'] == context['dir_name']:
                    album['hl_border'] = True
    else:
        # user selected an existing folder
        context['dir_name'] = name
        context['img_form'] = UploadPhotos()
        base_url = settings.MEDIA_URL + 'residents/' + resident.folder + '/photo_family/' + name + '/'
        # get all url to pictures in folder
        list_pictures = [base_url + path.split('/')[-1] for path in glob.glob(base_dir + name + '/*.*')]
        # newest picture display first
        list_pictures.sort(reverse=True)
        context['list_pictures'] = list_pictures
    return render(request, 'app4_ehpad_base/dir_photo_family.html', context)


@login_required
def record_passphrase(request):
    context = {}
    if request.method == 'POST':
        request.user.profileserenicia.passphrase.save('sample.wav', request.FILES.get('passphrase'))
        return redirect('app4_ehpad_base index')
    else:
        if request.user.profileserenicia.passphrase:
            context['exist'] = True
    return render(request, 'app4_ehpad_base/record_passphrase.html', context)


def get_random_pk(pk_list):
    return choice(pk_list)


def update_score(profileserenicia, word, intonation):
    profileserenicia.word_played += 1
    profileserenicia.total_score += (word.points * intonation.points)
    profileserenicia.save()


@login_required
def record_word(request, onboard):
    if request.method == 'POST':
        file_obj = request.FILES.get('word')
        word = WordToRecord.objects.get(pk=request.POST.get('filename'))
        intonation = IntonationToRecord.objects.get(pk=request.POST.get('dirname'))
        path = f"{settings.MEDIA_ROOT}/audio_record/common/{intonation.text}"
        Path(path).mkdir(parents=True, exist_ok=True)
        filename = word.text.replace(' ', '')
        with open(f"{path}/{filename}_{secrets.token_urlsafe()}.wav", 'wb+') as destination:
            for chunk in file_obj.chunks():
                destination.write(chunk)
        update_score(request.user.profileserenicia, word, intonation)
        if request.POST.get('end'):
            return redirect('app4_ehpad_base index')
    try:
        context = {
            'word': WordToRecord.objects.get(pk=get_random_pk(WordToRecord.objects.values_list('pk', flat=True))),
            'intonation': IntonationToRecord.objects.get(
                pk=get_random_pk(IntonationToRecord.objects.values_list('pk', flat=True))),
            'onboard': onboard}
    except (ObjectDoesNotExist, IndexError):
        return redirect('app4_ehpad_base index')
    return render(request, 'app4_ehpad_base/record_word.html', context)


@login_required
def face_reco(request):
    template = 'app4_ehpad_base/face_reco.html'
    context = {}
    if request.method == 'POST':
        if request.POST.get('identified_user'):
            try:
                # folder = request.POST.get('identified_user')
                folder, top10, unique_key = request.POST.get('identified_user').split('/')
                context['identified_user'] = User.objects.get(profileserenicia__folder=folder)
                # context['top_10'] = json.dumps([tmp.user.profileserenicia.folder for tmp in context['identified_user'].profileserenicia.user_list.all()[:10]])
                context['top_10'] = top10
                context['unique_key'] = unique_key
                # context['url_confirm'] = settings.FACIAL_RECO_IP + folder + '/' + unique_key + '/'
                # context['url_confirm'] = settings.FACIAL_RECO_IP + 'url_test/' + folder + '/'
                context['url_confirm'] = settings.FACIAL_RECO_IP + 'confirm_face/' + folder + '/' + unique_key + '/'
                template = 'app4_ehpad_base/face_reco_validation.html'
            except ObjectDoesNotExist:
                msg = str(_("Recognition impossible, please try again later"))
                return HttpResponseRedirect('/error/' + msg)
        elif request.POST.get('invalid'):
            top_faces = request.POST.get('top_10')
            top_faces = top_faces.replace('[', '').replace(']', '').replace(' ', '').replace("'", "")
            context['list_prof'] = ProfileSerenicia.objects.filter(folder__in=top_faces.split(','))
            context['unique_key'] = request.POST.get('unique_key')
            context.update(
                {'message': _('Help us improve our recognition by selecting the person you tried to identify'),
                 'category': _('It did not work ?')})
            template = 'app4_ehpad_base/select_top_reco.html'
        else:
            identified_user = User.objects.get(pk=request.POST.get('user_id'))
            if identified_user.groups.filter(permissions__codename__in=['view_residentehpad', 'view_residentrss', ]
                                             ).exists():
                actualize_resident_in_session(request.session, identified_user)
                if request.user.has_perm('app0_access.view_care'):
                    return redirect('caregiver')
            return redirect('app4_ehpad_base index')
    return render(request, template, context)


@login_required
def security_family(request):
    if request.session.get('resident_id'):
        request.session['client'] = Client.objects.get(
            profile__user__profileserenicia=request.session['resident_id']).id
        return render(request, 'app4_ehpad_base/security_family.html')
    return redirect('app4_ehpad_base index')
