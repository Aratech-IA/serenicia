from datetime import timedelta, datetime

from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import ObjectDoesNotExist
from django.db.models.functions import Lower
from django.http import HttpResponseRedirect, FileResponse
from django.shortcuts import render, redirect
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from app4_ehpad_base.models import PresentationType, ProfileSerenicia, PreferencesSerenicia
from app15_calendar.models import PlanningEvent, Event
from app9_personnalized_project.forms import NotationForm, CommentForm, StoryLifeForm
from app9_personnalized_project.models import Survey, SurveyResponse, Question, Comment, AppointmentSlot, Appointment, Unavailability, \
    StoryLifeTitle, StoryLife, ImportedProject


@login_required
@permission_required('app0_access.view_supportproject')
def index(request):
    if not request.user.has_perm('app0_access.view_family'):
        try:
            request.session.pop('resident_id')
        except KeyError:
            pass
    # get all last available survey for each resident
    query = Survey.objects.select_related('target',
                                          'target__user',
                                          'target__user__profile').filter(
        target__user__profile__in=request.user.profileserenicia.user_list.all(),
        is_active=True).order_by('target__user__last_name', 'target__user__first_name', '-date')\
        .distinct('target__user__last_name', 'target__user__first_name')
    display_filter = request.POST.get('display-filter')
    if display_filter == 'incomplete':
        list_survey = [{'survey': survey,
                        'answer': SurveyResponse.objects.filter(survey=survey,
                                                                interviewee=request.user.profileserenicia).first()}
                       for survey in query.exclude(filling_date__isnull=False)
                       if SurveyResponse.objects.filter(survey=survey,
                                                        interviewee=request.user.profileserenicia).exists()]
    elif display_filter == 'complete':
        list_survey = [{'survey': survey,
                        'answer': SurveyResponse.objects.filter(survey=survey,
                                                                interviewee=request.user.profileserenicia).first()}
                       for survey in query.filter(filling_date__isnull=False)]
    else:
        list_survey = [{'survey': survey,
                        'answer': SurveyResponse.objects.filter(survey=survey,
                                                                interviewee=request.user.profileserenicia).first()}
                       for survey in query]
    if not list_survey:
        msg = str(_("No survey available"))
        return HttpResponseRedirect('/error/' + msg)
    return render(request, 'app9_personnalized_project/index.html', {'listsurvey': list_survey, 'selected': display_filter})


def get_other_answer(surveyresponse):
    list_surv_res = SurveyResponse.objects.filter(survey=surveyresponse.survey).order_by(
        Lower('interviewee__user__last_name')).exclude(interviewee=surveyresponse.interviewee)
    other_int = []
    other_ans = {}
    for response in list_surv_res:
        tmp_data = {f'{notation.chapter.id}.{notation.question.id}': notation.notation.text
                    for notation in response.notation.all()}
        if tmp_data:
            other_int.append(response.interviewee)
            other_ans[response.interviewee.id] = tmp_data
    return other_int, other_ans


def are_chapters_completed(surveyresponse):
    quest_nb = Question.objects.filter(chapter__referees__in=surveyresponse.interviewee.user.groups.all(),
                                       chapter__survey=surveyresponse.survey).count()
    if quest_nb != surveyresponse.notation.count():
        return False
    return True


def get_activity_eval_data(survey):
    list_events = PlanningEvent.objects.filter(participants=survey.target, event__is_activity=True).exclude(start__gt=timezone.localtime())
    previous_survey = Survey.objects.filter(target=survey.target, filling_date__isnull=False).exclude(id=survey.id).last()
    if previous_survey:
        start = get_combined_aware_datetime(previous_survey.filling_date, timezone.localtime())
    elif list_events:
        start = list_events.first().start
    else:
        return False
    list_events = list_events.filter(start__gte=start).order_by('-start')
    result = {'start': start, 'data': {}}
    for pl_event in list_events:
        if not result['data'].get(pl_event.event.type):
            result['data'][pl_event.event.type] = {'registered': 1, 'participated': 0, 'last_register': pl_event.start}
        else:
            result['data'][pl_event.event.type]['registered'] += 1
        if survey.target in pl_event.attendance.all():
            result['data'][pl_event.event.type]['participated'] += 1
    return result


@login_required
@permission_required('app0_access.view_supportproject')
def survey_answering(request, survey_id):
    context = {}
    try:
        survey = Survey.objects.get(id=survey_id)
    except ObjectDoesNotExist:
        msg = str(_("No survey available"))
        return HttpResponseRedirect('/error/' + msg)
    surveyresponse, is_created = SurveyResponse.objects.get_or_create(survey=survey,
                                                                      interviewee=request.user.profileserenicia)
    answer = surveyresponse.notation
    try:
        visibility = PreferencesSerenicia.objects.get(profile=survey.target.user.profile).interventions
    except ObjectDoesNotExist:
        visibility = 'no-answer'
    if request.method == 'POST':
        chapter = request.POST.get('chapter')
        if request.POST.get('update-com'):
            Comment.objects.filter(pk=request.POST.get('update-com')).update(text=request.POST.get('text-update'))
        elif request.POST.get('finalize'):
            survey.filling_date = timezone.localdate()
            survey.save()
        elif request.POST.get('comment'):
            comment_form = CommentForm({'text': request.POST.get('comment'), 'chapter': chapter,
                                        'surveyresponse': surveyresponse})
            if comment_form.is_valid():
                comment_form.save()
            elif not comment_form.validate_unique():
                Comment.objects.filter(chapter=chapter,
                                       surveyresponse=surveyresponse).update(text=request.POST.get('comment'))
        elif request.POST.get('choice'):
            chapter = (request.POST.get('choice').split('.'))[0]
            choices = {'chapter': chapter,
                       'question': (request.POST.get('choice').split('.'))[1],
                       'notation': (request.POST.get('choice').split('.'))[2]}
            form = NotationForm(choices)
            if form.is_valid():
                answer = form.save(answer)
                surveyresponse.last_update = timezone.localtime()
                surveyresponse.save()
        elif request.POST.get('meal_type'):
            survey.target.meal_type = PresentationType.objects.get(id=request.POST.get('meal_type'))
            survey.target.save()
        elif request.POST.get('visibility'):
            visibility = request.POST.get('visibility')
            if visibility == 'no-answer':
                PreferencesSerenicia.objects.get(profile=survey.target.user.profile).delete()
            else:
                pref = PreferencesSerenicia.objects.get_or_create(profile=survey.target.user.profile)[0]
                pref.interventions = visibility
                pref.save()
                visibility = int(visibility)
        context['last_chapter'] = chapter
    if not survey.filling_date:
        if survey.created_by == request.user.profileserenicia:
            context['readonly'] = False
        elif are_chapters_completed(surveyresponse):
            context['readonly'] = True
    else:
        context['readonly'] = True
    context['answer'] = [f'{notation.chapter.id}.{notation.question.id}.{notation.notation.id}'
                         for notation in answer.all()]
    context['other_int'], context['other_ans'] = get_other_answer(surveyresponse)
    context['other_com'] = Comment.objects.filter(surveyresponse__survey=survey).exclude(surveyresponse=surveyresponse)
    context['comment'] = [{'text': com.text, 'chapter': com.chapter.id} for com in
                          Comment.objects.filter(surveyresponse=surveyresponse)]
    context['survey'] = survey
    context['date'] = {'filled': survey.filling_date}
    last_answer = SurveyResponse.objects.filter(survey=survey).order_by('last_update').last()
    if last_answer:
        context['date']['update'] = last_answer.last_update
    context['presentation_type'] = PresentationType.objects.order_by(Lower('type'))
    context['activity'] = get_activity_eval_data(survey)
    context['visibility'] = {'choices': PreferencesSerenicia.INTERVENTIONS_CHOICES, 'selected': visibility}
    return render(request, 'app9_personnalized_project/survey.html', context)


def get_support_project_modal_data(resident):
    project = Survey.objects.filter(target=resident, filling_date__isnull=False).order_by('date').last()
    try:
        surveyresponse = SurveyResponse.objects.get(interviewee=project.created_by, survey=project)
        comments = Comment.objects.filter(surveyresponse=surveyresponse)
        return {'project': surveyresponse, 'comments': comments}
    except AttributeError:
        return False
    except ObjectDoesNotExist:
        try:
            old_project = ImportedProject.objects.get(target=resident)
            return {'project': old_project, 'pdf': True}
        except ObjectDoesNotExist:
            return False


def get_story_life_modal_data(resident):
    return StoryLife.objects.filter(resident=resident, cannot_answer=False).exclude(text='')


def get_combined_aware_datetime(date, time):
    return datetime(year=date.year, month=date.month, day=date.day, hour=time.hour, minute=time.minute,
                    tzinfo=timezone.localtime().tzinfo)


def next_appointment(date, app_type):
    next_slot = False
    if AppointmentSlot.objects.filter(day=date.weekday()).count() > 1:
        next_slot = AppointmentSlot.objects.filter(day=date.weekday(), type=app_type, start__gt=date.time())
    if not next_slot:
        next_slot = AppointmentSlot.objects.filter(day__gt=date.weekday(), type=app_type)
    if not next_slot:
        date = date + timedelta(weeks=1)
        next_slot = AppointmentSlot.objects.filter(day__gte=0, type=app_type)
    next_slot = next_slot.order_by('day', 'start').first()
    monday = date - timedelta(days=date.weekday())
    next_date = monday + timedelta(days=next_slot.day)
    return {'start': get_combined_aware_datetime(next_date, next_slot.start),
            'end': get_combined_aware_datetime(next_date, next_slot.end)}


def get_support_project_event(organizer):
    return Event.objects.get_or_create(type='support project', organizer=organizer)[0]


def is_slot_already_reserved(slot, event, app_type):
    if PlanningEvent.objects.filter(event=event,
                                    start=slot['start'], end=slot['end']).exists():
        return True
    if Unavailability.objects.filter(start__lte=slot['start'], end__gte=slot['start'], type=app_type).exists():
        return True
    return False


def get_next_free_slot(date, event):
    app_type = {'support project': 'support_project', 'demonstration': 'demo'}
    selected_type = app_type[event.type]
    slot = next_appointment(date, selected_type)
    while is_slot_already_reserved(slot, event, selected_type):
        slot = next_appointment(date, selected_type)
        date = slot['start']
    return slot


def get_list_next_slots(len_list, event):
    slot = get_next_free_slot(timezone.localtime(), event)
    result = []
    while len(result) < len_list:
        result.append(slot)
        slot = get_next_free_slot(slot['start'], event)
    return result


def create_appointment(profileserenicia, planning_event, by_video=False, confirmed=False, owner=False):
    return Appointment.objects.create(profileserenicia=profileserenicia, planning_event=planning_event,
                                      by_video=by_video, confirmed=confirmed, owner=owner)


@login_required
@permission_required('app0_access.view_supportproject')
def appointments(request):
    context = {}
    try:
        resident = ProfileSerenicia.objects.get(user__id=request.session['resident_id'])
        survey = Survey.objects.filter(target=resident, filling_date__isnull=True).order_by('date').last()
        if not survey or not AppointmentSlot.objects.filter(type='support_project'):
            raise ObjectDoesNotExist
    except ObjectDoesNotExist:
        return redirect('app4_ehpad_base index')
    event = get_support_project_event(survey.created_by)
    if request.method == 'POST':
        by_video = {'presence': False, 'distance': True}
        if request.POST.get('delete'):
            PlanningEvent.objects.get(id=request.POST.get('delete')).delete()
        elif request.POST.get('confirmation'):
            rejected = {'rejected': True, 'confirmed': False}
            Appointment.objects.filter(pk=request.POST.get('confirmation')) \
                .update(by_video=by_video.get(request.POST.get('type-select')), confirmed=True,
                        rejected=rejected.get(request.POST.get('participation')))
        elif request.POST.get('cancel'):
            Appointment.objects.filter(pk=request.POST.get('cancel')).update(rejected=True)
        else:
            selected_date = datetime.strptime(request.POST.get('date-select'), '%Y-%m-%d-%H-%M')
            slot = AppointmentSlot.objects.get(day=selected_date.weekday(), start=selected_date.time(),
                                               type='support_project')
            planning_ev = PlanningEvent.objects.create(event=event,
                                                       start=get_combined_aware_datetime(selected_date.date(),
                                                                                         slot.start),
                                                       end=get_combined_aware_datetime(selected_date.date(), slot.end))
            selected_prof = ProfileSerenicia.objects.filter(id__in=request.POST.getlist('profile-select'))
            planning_ev.participants.add(*selected_prof)
            planning_ev.participants.add(resident)
            planning_ev.participants.add(request.user.profileserenicia)
            create_appointment(request.user.profileserenicia, planning_ev,
                               by_video=by_video.get(request.POST.get('type-select')), confirmed=True, owner=True)
            [create_appointment(profileserenicia, planning_ev) for profileserenicia in selected_prof]
            context.update({'category': _('Appointment'), 'message': _('Your appointment has been registered')})
    context['list_slot'] = get_list_next_slots(15, event)
    context['list_profile'] = ProfileSerenicia.objects.filter(user_list=resident.user.profile,
                                                              user__groups__permissions__codename='view_family') \
        .exclude(user=request.user).order_by(Lower('user__last_name'), Lower('user__first_name'))
    list_appointments = Appointment.objects.filter(profileserenicia=request.user.profileserenicia,
                                                   rejected=False).order_by('planning_event__start')
    wait_confirm = list_appointments.filter(owner=False, confirmed=False, rejected=False).first()
    context.update({'appointments': list_appointments.filter(confirmed=True), 'waiting_confirmation': wait_confirm,
                    'resident': resident})
    return render(request, 'app9_personnalized_project/appointments.html', context)


def get_data(planning_event):
    return {'start': planning_event.start, 'end': planning_event.end, 'planning_id': planning_event.id,
            'resident': planning_event.participants.get(user__groups__permissions__codename='view_residentehpad'),
            'participants': Appointment.objects.filter(planning_event=planning_event, confirmed=True, rejected=False)
                .order_by(Lower('profileserenicia__user__last_name'),
                          Lower('profileserenicia__user__first_name'))}


@login_required
@permission_required('app0_access.view_supportproject')
def employee_appointments(request):
    try:
        request.session.pop('resident_id')
    except KeyError:
        pass
    context = {}
    if request.POST.get('delete'):
        PlanningEvent.objects.filter(id=request.POST.get('delete')).delete()
        context.update({'category': _('Appointment'), 'message': _('The appointment has been deleted')})
    context['appointments'] = [get_data(planning_event) for planning_event in
                               PlanningEvent.objects.filter(
                                   event=get_support_project_event(request.user.profileserenicia),
                                   start__gte=timezone.localtime())]
    if not context['appointments']:
        msg = _("You don't have any appointment yet.")
        return redirect('error message', msg=msg)
    return render(request, 'app9_personnalized_project/appointments_employee.html', context)


@login_required
@permission_required('app0_access.view_supportproject')
def story_life(request, res_id):
    msg = None
    resident = ProfileSerenicia.objects.get(id=res_id)
    if resident.user.profile not in request.user.profileserenicia.user_list.all():
        return redirect('app9_personnalized_project index')
    if request.method == 'POST':
        if request.POST.get('delete'):
            StoryLife.objects.filter(resident=resident, title__id=request.POST.get('title')).delete()
            msg = {'category': _('Saved'), 'message': _('The story life has been deleted')}
        else:
            form = StoryLifeForm(request.POST)
            if form.is_valid():
                form.save(resident=resident, title=StoryLifeTitle.objects.get(id=request.POST.get('title')))
                msg = {'category': _('Saved'), 'message': _('The modifications has been saved')}
    context = {'titles': [], 'answers': StoryLife.objects.filter(resident=resident)}
    for title in StoryLifeTitle.objects.all():
        try:
            form = StoryLifeForm(instance=context['answers'].get(title=title), auto_id=f'%s_{title.id}')
        except ObjectDoesNotExist:
            form = StoryLifeForm()
        context['titles'].append({'form': form, 'object': title})
    if msg:
        context.update(msg)
    return render(request, 'app9_personnalized_project/story_life.html', context)


def imported_project_pdf(request, import_id):
    project = ImportedProject.objects.get(id=import_id)
    return FileResponse(project.file, as_attachment=True, filename=f'{project.target} - {project.date}')
