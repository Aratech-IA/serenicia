from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Avg
from django.db.models.functions import Lower
from django.http import HttpResponseRedirect
from django.shortcuts import render, redirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from numpy.random import randint
from django.utils import timezone

from app10_social_activities.forms import UploadPhoto, CommentForm
from app10_social_activities.models import Question, Evaluation, Photo, get_activity_photos_path
from app4_ehpad_base.models import ProfileSerenicia
from app15_calendar.models import PlanningEvent, PlanningEventPhotos
from app15_calendar.views import calendar_configuration


@login_required
@permission_required('app0_access.view_animation')
def selection_activity(request):
    try:
        request.session.pop('resident_id')
    except KeyError:
        pass
    if request.POST.get('selected'):
        request.session['act_id'] = request.POST.get('selected')
        return redirect('app10_social_activities activity index')
    now = timezone.localtime()
    list_activity = PlanningEvent.objects.filter(start__date=now.date(),
                                                 event__is_activity=True).order_by('start')
    if list_activity.count():
        return render(request, 'app10_social_activities/selection_activity.html', {'list_act': list_activity, 'now': now})
    else:
        msg = str(_("No activity today"))
        return HttpResponseRedirect('/error/' + msg)


def get_selected_activity(act_id):
    if not act_id:
        return redirect('app10_social_activities index')
    return PlanningEvent.objects.prefetch_related('event', 'participants', 'attendance').get(pk=act_id)


def has_voted(participant, activity):
    if not Evaluation.objects.filter(question__is_active=True, voter=participant,
                                     activity_new=activity).count() == Question.objects.filter(is_active=True).count():
        return False
    return True


@login_required
@permission_required('app0_access.view_animation')
def activity_index(request):
    context = {}
    activity = get_selected_activity(request.session.get('act_id'))
    if activity.end.date() < timezone.localtime().date():
        request.session.pop('act_id')
        return redirect('app10_social_activities index')
    now = timezone.localtime()
    if request.method == 'POST':
        if request.FILES.get('file'):
            photo_form = UploadPhoto(request.POST, request.FILES)
            if photo_form.is_valid():
                photo = photo_form.save()
                photo.added_by = User.objects.get(id=request.user.id)
                photo.save()
                PlanningEventPhotos.objects.create(photos=photo, planning_event=activity)
                context['message'] = _('Photo successfully sent !')
                context['category'] = _('Activity photo')
        elif request.POST.get('ending_validation'):
            activity.end = now
            activity.save()
            context['category'] = activity.event.type
            context['message'] = _('Evaluation available for') + " " + str(activity.attendance.count()) + " " + _(
                'participants')
        elif request.POST.get('ending'):
            context['ask_validation'] = True
            duration = str(now - activity.start).split('.')[0]
            context['duration'] = datetime.strptime(duration, '%H:%M:%S')
        elif request.POST.get('event_comment'):
            comment_form = CommentForm(data=request.POST, instance=activity)
            if comment_form.is_valid():
                comment_form.save()
                context['category'] = activity.event.type
                context['message'] = _('Comment saved !')
    context['comment_form'] = CommentForm(instance=activity)
    context['photo_activity'] = UploadPhoto()
    context['activity'] = activity
    context['now'] = now
    context['voter_count'] = len([voter for voter in activity.attendance.all() if has_voted(voter, activity)])
    if activity.end <= timezone.localtime():
        if context['voter_count'] < activity.attendance.count():
            context['access_to_rating'] = True
    return render(request, 'app10_social_activities/index.html', context)


@login_required
@permission_required('app0_access.view_animation')
def dashboard(request):
    return render(request, 'app10_social_activities/dashboard.html')


@login_required
@permission_required('app0_access.view_animation')
def add_resident(request):
    activity = get_selected_activity(request.session.get('act_id'))
    list_resident = ProfileSerenicia.objects.filter(
        status='home', user__is_active=True, user__groups__permissions__codename__in=
        ['view_residentehpad', 'view_residentrss', ]).order_by('user__last_name')
    list_resident = [resident for resident in list_resident if resident not in activity.participants.all()]
    return render(request, 'app10_social_activities/select_resident.html', {'list_resident': list_resident})


@login_required
@permission_required('app0_access.view_animation')
def attendance(request):
    context = {}
    activity = get_selected_activity(request.session.get('act_id'))
    if request.method == 'POST':
        participant_id = None
        if request.POST.get('selected'):
            selected_resident = ProfileSerenicia.objects.get(id=request.POST.get('selected'))
            activity.participants.add(selected_resident)
            activity.attendance.add(selected_resident)
            participant_id = selected_resident.id
        else:
            if request.POST.get('add'):
                participant_id = request.POST.get('add')
                activity.attendance.add(ProfileSerenicia.objects.get(id=participant_id))
            elif request.POST.get('remove'):
                participant_id = request.POST.get('remove')
                activity.attendance.remove(ProfileSerenicia.objects.get(id=participant_id))
        context['saved'] = int(participant_id)
    context['has_voted'] = [evaluation.voter.id for evaluation in
                            Evaluation.objects.filter(activity_new=activity).distinct('voter')]
    context['activity'] = activity
    return render(request, 'app10_social_activities/attendance_list.html', context)


def get_first_question(request):
    try:
        first_q = Question.objects.filter(is_active=True).order_by('order').first().order
    except AttributeError:
        return render(request, 'app10_social_activities/index.html', {'message': _('You haven\'t created any questions yet'),
                                                    'category': _('Evaluation')})
    return first_q


@login_required
@permission_required('app0_access.view_animation')
def start_evaluation(request):
    if request.POST.get('invalid.x'):
        return redirect('app10_social_activities auto identification')
    elif request.POST.get('valid.x'):
        first_question = get_first_question(request)
        request.session['voter'] = request.POST.get('voter')
        return redirect('app10_social_activities evaluate', question=first_question)
    return redirect('app10_social_activities index')


@login_required
@permission_required('app0_access.view_animation')
def select_voter(request):
    activity = get_selected_activity(request.session.get('act_id'))
    context = {'activity': activity,
               'list_att': [{'participant': participant, 'has_voted': has_voted(participant, activity)}
                            for participant in activity.attendance.order_by('user__last_name')]}
    context['list_att'].append(
        {'participant': activity.event.organizer, 'has_voted': has_voted(activity.event.organizer, activity)})
    return render(request, 'app10_social_activities/select_voter.html', context)


def get_random_picture(activity, voter):
    pics_from_activity = Photo.objects.prefetch_related('identified').filter(activity_new=activity)
    if pics_from_activity.filter(identified=voter).exists():
        pics_from_activity = pics_from_activity.filter(identified=voter)
    if pics_from_activity.exists():
        return pics_from_activity.__getitem__(randint(0, pics_from_activity.count())).img


@login_required
@permission_required('app0_access.view_animation')
def evaluate(request, question):
    activity = get_selected_activity(request.session.get('act_id'))
    question = Question.objects.get(order=question, is_active=True)
    try:
        voter = activity.attendance.get(folder=request.session['voter'])
    except ObjectDoesNotExist:
        if request.session['voter'] == activity.event.organizer.folder:
            voter = activity.event.organizer
        else:
            return redirect('app10_social_activities activity index')
    if request.POST.get('vote'):
        vote = None
        for key in request.POST.keys():
            if '.x' in key:
                vote = key.split('.')[0]
                break
        if vote:
            evaluation, is_created = Evaluation.objects.update_or_create(voter=voter,
                                                                         activity_new=activity,
                                                                         question=question)
            evaluation.note = vote
            evaluation.save()
        next_question = Question.objects.filter(order__gt=question.order, is_active=True).first()
        if not next_question:
            return redirect('app10_social_activities activity index')
        question = next_question
    image_url = ''
    try:
        if question.subject == 'location':
            image_url = activity.event.location.photo.url
        elif question.subject == 'contents':
            pic_from_activity = get_random_picture(activity, voter)
            image_url = pic_from_activity.url
    except (AttributeError, ValueError):
        image_url = settings.STATIC_URL + 'app4_ehpad_base/img/no_picture.png'
    return render(request, 'app10_social_activities/evaluate.html', {'activity': activity,
                                                   'question': question,
                                                   'background_img': image_url})


@login_required
@permission_required('app0_access.view_animation')
def auto_identification(request):
    if request.method == 'POST':
        if request.POST.get('folder'):
            identified_user = ProfileSerenicia.objects.select_related('user', 'user__profile').get(
                folder=request.POST.get('folder'))
            return render(request, 'app10_social_activities/validation_identification.html', {'identified_user': identified_user})
    return render(request, 'app10_social_activities/auto_identification.html')


def truncate_notation(notation):
    return float(str(notation.get('note__avg'))[:3])


def get_average_notation(list_eval):
    result = list_eval.aggregate(Avg('note'))
    try:
        result = truncate_notation(result)
    except ValueError:
        result = None
    return result


@login_required
@permission_required('app0_access.view_animation')
def historic(request):
    context = {}
    now = timezone.localtime()
    try:
        request.session.pop('resident_id')
    except KeyError:
        pass
    if request.method == 'POST':
        year = int(request.POST.get('year'))
        month = int(request.POST.get('month'))
        if 'previous.x' in request.POST:
            month -= 1
            if month < 1:
                month = 12
                year -= 1
        elif 'next.x' in request.POST:
            month += 1
            if month > 12:
                month = 1
                year += 1
    else:
        month = now.month
        year = now.year
    context['list_act'] = [
        {'note': get_average_notation(Evaluation.objects.filter(activity_new=activity)), 'object': activity}
        for activity in PlanningEvent.objects.filter(end__lte=timezone.localtime(),
                                                     end__date__month=month,
                                                     end__date__year=year, event__is_activity=True).order_by('start')]
    context['option'] = month
    context['year'] = year
    return render(request, 'app10_social_activities/historic.html', context)


def is_present(participant, list_attendance):
    if participant in list_attendance:
        return True
    return False


@login_required
@permission_required('app0_access.view_animation')
def historic_details(request, act_id):
    context = {}
    activity = PlanningEvent.objects.get(pk=act_id)
    path, url = get_activity_path_and_url(activity)
    if Path(path).exists():
        context['pic_available'] = True
    list_eval = Evaluation.objects.prefetch_related('voter', 'voter__user', 'question',
                                                    'voter__user__profile').filter(activity_new=activity)
    context['act_rating'] = get_average_notation(list_eval)
    list_participants = [{'profilej': participant, 'is_present': is_present(participant, activity.attendance.all())}
                         for participant in activity.participants.order_by(Lower('user__last_name'))]
    context['list_participants'] = sorted(list_participants, key=lambda x: x['is_present'], reverse=True)
    context['list_voter'] = [{'object': evaluation.voter,
                              'note': get_average_notation(list_eval.filter(voter=evaluation.voter)),
                              'list_eval': list_eval.filter(voter=evaluation.voter)}
                             for evaluation in list_eval.distinct('voter')]
    context['activity'] = activity
    return render(request, 'app10_social_activities/details.html', context)


def get_activity_path_and_url(activity):
    last_part = get_activity_photos_path(activity)
    # ligne ci-dessous pour tests locaux uniquement !!
    # last_part = 'activities/RotEMrsTcEKXngJ5mFPb5iI4S6XdsR5r30PCfTsxHWE/2021-09-17_1'
    return f'{settings.MEDIA_ROOT}/{last_part}', f'{settings.MEDIA_URL}{last_part}'


@login_required
@permission_required('app0_access.view_animation')
def gallery(request, act_id):
    try:
        activity = PlanningEvent.objects.get(id=act_id)
    except ObjectDoesNotExist:
        return redirect('app10_social_activities index')
    path, url = get_activity_path_and_url(activity)
    context = {'list_url': [{'thumb': f'{url}/thumbnails/{pic.name}', 'full': f'{url}/{pic.name}'}
                            for pic in Path(path).glob('*') if not pic.is_dir()], 'activity': activity}
    if request.method == 'POST':
        context['selection_mod'] = True
        if request.POST.get('selected'):
            selected = request.POST.get('selected')
            if activity.thumbnail_url == selected:
                activity.thumbnail_url = ''
                context['save_message'] = _('The illustration photo has been removed')
            else:
                activity.thumbnail_url = selected
                context['save_message'] = _('The illustration photo has been added')
            activity.save()
            request.session['act_id'] = act_id
    if '/historic/' in request.META.get('HTTP_REFERER'):
        context['redirect_url'] = reverse('app10_social_activities historic details', args=[act_id])
    else:
        request.session['act_id'] = act_id
        context['redirect_url'] = reverse('app10_social_activities activity index')
    return render(request, 'app10_social_activities/gallery.html', context)


def gallery_details(request, act_id):
    pic_url = request.POST.get('pic_url')
    if pic_url:
        return render(request, 'app10_social_activities/gallery_details.html',
                      {'pic_url': pic_url, 'act_id': act_id, 'redirect_url': request.META.get('HTTP_REFERER')})
    return redirect('app10_social_activities gallery', act_id=act_id)


def get_social_life_data(profileserenicia):
    result = []
    last_activity = PlanningEvent.objects.filter(participants=profileserenicia, event__public=True,
                                                 end__lte=timezone.localtime(),
                                                 end__year=timezone.localtime().year, event__is_activity=True)
    if not last_activity.count():
        last_activity = PlanningEvent.objects.filter(participants=profileserenicia, event__public=True,
                                                     end__lte=timezone.localtime(),
                                                     end__year=(timezone.localtime().year - 1),
                                                     event__is_activity=True)
    else:
        last_activity = last_activity.order_by('-end')[:4]
    for activity in last_activity[:5]:
        total_eval = Evaluation.objects.filter(activity_new=activity)
        tmp_result = {'activity': activity, 'global': get_average_notation(total_eval),
                      'resident_eval': get_average_notation(total_eval.filter(voter=profileserenicia))}
        if activity.thumbnail_url:
            tmp_result['img_url'] = activity.thumbnail_url
        else:
            try:
                pic_from_activity = get_random_picture(activity, profileserenicia)
                tmp_result['img_url'] = pic_from_activity.url
            except (AttributeError, ValueError):
                tmp_result['img_url'] = settings.STATIC_URL + 'app4_ehpad_base/img/homemade_svg/outdoor_activity_64x64.svg'
        result.append(tmp_result)
    return result


def planning(request):
    try:
        request.session.pop('resident_id')
    except KeyError:
        pass
    activities = request.POST.get('activities', 'all')
    events = PlanningEvent.objects.filter(event__is_activity=True)
    if activities == 'user':
        events = events.filter(event__organizer=request.user.profileserenicia)
    calendar = calendar_configuration(display='month', editable=request.user.has_perm('app15_calendar.view_planningevent'),
                                      events=events)
    return render(request, 'app10_social_activities/planning.html', {'calendar': calendar, 'activities': activities})
