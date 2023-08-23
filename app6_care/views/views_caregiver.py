import json
from datetime import timedelta, datetime
import pytz
from dateutil import parser

from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.utils import timezone

from app11_quality.models import Protocol_list
from app4_ehpad_base.views import actualize_resident_in_session
from app6_care.filters import ASInterventionFilter
from projet.settings.settings import USER_LANGUAGE, TIME_ZONE

from app1_base.models import User, Profile
from app6_care.models import FreeComment, TaskInTreatmentPlan, InterventionTreatmentPlan, \
    TmpInterventionTreatmentPlanForWebsocket, Intervention, TaskLevel2, TreatmentsPlan, TaskLevel1, TaskLevel3, \
    TaskLevel4, TaskComment
from app6_care.forms.forms_intervention import FreeCommentForm, PlanDeSoinForm
from app6_care.netsoins_api import post_free_comment
from app6_care.views.intervention import intervention


@login_required
def views_caregiver(request):
    if request.POST.get('free_comment'):
        return redirect('caregiver_free_comment')
    elif request.POST.get('next-res') or request.POST.get('previous-res'):
        actual_user = Profile.objects.get(user__id=request.session['resident_id'])
        count = actual_user.client.room_number
        next_room = None
        while next_room is None:
            if request.POST.get('next-res'):
                if count > 700:
                    count = 100
                count = count + 1
            elif request.POST.get('previous-res'):
                if count < 100:
                    count = 700
                count = count - 1
            try:
                next_room = Profile.objects.get(client__room_number=count)
            except ObjectDoesNotExist:
                pass
        # new = User.objects.get(id=2580)
        actualize_resident_in_session(request.session, next_room.user)
    return render(request, 'app6_care/caregiver/caregiver.html', intervention(request, 'AS', True))


@login_required
def views_caregiver_free_comment(request):
    if request.method == 'POST':
        form = FreeCommentForm(request.POST)
        if form.is_valid():
            free_comment = FreeComment.objects.create(patient=User.objects.get(pk=request.session['resident_id']), content=form.cleaned_data['content'], nurse=request.user, profession='AS')
            post_free_comment(free_comment)
            return redirect('caregiver')

    else:
        form = FreeCommentForm()
    return render(request, 'app6_care/caregiver/free_comment.html', {'form': form})


@login_required
def views_showers_report(request):
    try:
        request.session.pop('resident_id')
    except KeyError:
        pass
    last_monday = (timezone.now() - timedelta(days=(timezone.now().weekday() % 7)))
    last_monday = last_monday.replace(hour=0, minute=0, second=0, microsecond=0)

    residents = User.objects.filter(
        groups__permissions__codename='view_residentehpad', is_active=True).exclude(
        profileserenicia__status='deceased', groups__permissions__codename='view_residentehpad')

    residents_who_took_a_shower_since_monday = User.objects.filter(
        groups__permissions__codename='view_residentehpad', is_active=True, patient__end__gte=last_monday,
        patient__details__task_level_2__name="Douche").exclude(
        profileserenicia__status='deceased', groups__permissions__codename='view_residentehpad').order_by(
        'profile__client__room_number').distinct('profile__client__room_number')

    def has_room_number(resident):
        try:
            resident.profile.client.room_number
            return True
        except (ObjectDoesNotExist, AttributeError):
            return False

    residents = [resident for resident in list(residents) if has_room_number(resident)]
    residents_who_took_a_shower_since_monday = [
        resident for resident in list(residents_who_took_a_shower_since_monday) if has_room_number(resident)]

    others = list(set(residents) - set(residents_who_took_a_shower_since_monday))
    others = sorted(others, key=lambda other: other.profile.client.room_number)

    return render(request, 'app6_care/caregiver/showers_report.html',
                  {'residents_who_took_a_shower_since_monday': residents_who_took_a_shower_since_monday,
                   'others': others})


def check_if_need_an_alert(resident, inter, count):
    inter = Intervention.objects.filter(patient=resident, type__details__name=inter).last()
    if not inter or inter.end is not None and inter.end < datetime.now(pytz.utc) - timedelta(days=7):
        count[0] += 1
        return True
    else:
        return False


@login_required
def views_interventions_report(request):
    try:
        request.session.pop('resident_id')
    except KeyError:
        pass
    filter = ASInterventionFilter(request.GET, queryset=Intervention.objects.all().order_by('-start'))

    resident_list = User.objects.filter(groups__permissions__codename='view_residentehpad', is_active=True).exclude(profileserenicia__status='deceased')
    alerts = {}
    for resident in resident_list:
        count = [0]
        shower_alert = check_if_need_an_alert(resident, 'Douche', count)
        pee_alert = check_if_need_an_alert(resident, 'Urine', count)
        poop_alert = check_if_need_an_alert(resident, 'Selle', count)
        clean_ground_alert = check_if_need_an_alert(resident, 'Sol', count)
        alerts[resident] = {'shower_alert': shower_alert, 'pee_alert': pee_alert, 'poop_alert': poop_alert,
                            'ground_alert': clean_ground_alert, 'count': count[0]}

    return render(request, 'app6_care/caregiver/interventions_report.html', {'filter': filter, 'alerts': alerts})


@login_required
def views_caregiver_treatment_plan(request, patient_id, profession):
    if request.method == 'POST':
        click_on_event(json.loads(request.body), request.user, patient_id, profession)

    # target date
    # days_to_display
    # duration
    target_date = timezone.now()
    days_to_display = 60
    events = get_events(patient_id, profession, target_date, days_to_display)
    # events = get_events2(patient_id, profession)

    websocket_url = 'wss://' + request.get_host() + ':' + request.META.get('SERVER_PORT') + '/app6_care/app6_websocket/'

    return render(request, 'app6_care/caregiver/treatments_plan.html', {'patient_id': patient_id, 'profession': profession,
                                                                   'user_language': USER_LANGUAGE, 'events': events,
                                                                   'websocket_url': websocket_url})


@login_required
def last_comments(request):
    result = TaskComment.objects.filter(intervention__patient__pk=request.session['resident_id']).order_by('-intervention__start')[:10]
    return render(request, 'app6_care/caregiver/last_comments.html', {'comments': result})


def get_events2(patient_id, profession):
    events = []
    for loop in range(29):
        tasks = TaskInTreatmentPlan.objects.filter(treatments_plan__patient__pk=patient_id, day_in_cycle=loop)
        for task in tasks:
            formatted_start_time = datetime(year=2018, month=1, day=loop,
                                            hour=task.start_time.hour, minute=task.start_time.minute, microsecond=0
                                            ).astimezone(pytz.timezone(TIME_ZONE))
            if InterventionTreatmentPlan.objects.filter(
                    treatment_plan_task=task, patient=User.objects.get(pk=patient_id), profession=profession).exists():
                # green task means the task has been done, conversely orange task means the task is not done
                background_color = '#93a9d2'
            else:
                background_color = 'orange'
            if task.task_level_2:
                title = task.task_level_2.name
                duration = task.task_level_2.duration
                task_level = 2
            elif task.task_level_3:
                title = task.task_level_3.name
                duration = task.task_level_3.duration
                task_level = 3
            else:
                title = task.task_level_4.name
                duration = task.task_level_4.duration
                task_level = 4

            events.append(
                {'id': task.id,
                 'title': title,
                 'task_level': task_level,
                 'start': formatted_start_time.isoformat(),
                 'end': (formatted_start_time + duration).isoformat(),
                 'backgroundColor': background_color,
                 })
    print(f'print de get_event2 : {events}')
    return events


def get_events(patient_id, profession, target_date, days_to_display):
    events = []
    # tartget_date : the date on which days_to_display will be calculated,
    # 2018-01-01 has been chosen arbitrarily because it is a Monday, but in fact reference date could be anything else
    reference_date = datetime(year=2018, month=1, day=1, microsecond=0).astimezone(pytz.timezone(TIME_ZONE))
    passed_four_weeks_cycles = divmod((target_date - reference_date).days, 28)
    cycle, day_of_cycle = passed_four_weeks_cycles[0], passed_four_weeks_cycles[1]

    for loop in range(days_to_display):
        tasks = TaskInTreatmentPlan.objects.filter(treatments_plan__patient__pk=patient_id,
                                                   day_in_cycle=day_of_cycle)
        for task in tasks:
            start_time = task.start_time
            formatted_start_time = datetime(year=target_date.year, month=target_date.month, day=target_date.day,
                                            hour=start_time.hour, minute=start_time.minute, microsecond=0
                                            ).astimezone(pytz.timezone(TIME_ZONE))

            if InterventionTreatmentPlan.objects.filter(
                    treatment_plan_task=task, patient=User.objects.get(pk=patient_id),
                    planned_time=formatted_start_time, profession=profession).exists():
                # green task means the task has been done, conversely orange task means the task is not done
                background_color = '#93a9d2'
            else:
                background_color = 'orange'

            if task.task_level_2:
                title = task.task_level_2.name
                duration = task.task_level_2.duration
                task_level = 2
            elif task.task_level_3:
                title = task.task_level_3.name
                duration = task.task_level_3.duration
                task_level = 3
            else:
                title = task.task_level_4.name
                duration = task.task_level_4.duration
                task_level = 4
            print(loop)
            events.append(
                {'id': task.id,
                 'title': title,
                 'task_level': task_level,
                 'start': formatted_start_time.isoformat(),
                 'end': (formatted_start_time + duration).isoformat(),
                 'backgroundColor': background_color,
                 })

        target_date = target_date + timedelta(days=1)
        if day_of_cycle < 28:
            day_of_cycle += 1
        else:
            day_of_cycle = 1
            cycle += 1
    print(events)
    return events


def click_on_event(body, user, patient_id, profession):
    treatment_plan_task = TaskInTreatmentPlan.objects.get(pk=body['id'])
    planned_time = parser.isoparse(body['start']).astimezone(pytz.timezone(TIME_ZONE))
    patient = User.objects.get(pk=patient_id)

    try:
        intervention_treatment_plan = InterventionTreatmentPlan.objects.get(
            treatment_plan_task=treatment_plan_task, nurse=user, patient=patient, planned_time=planned_time,
            profession=profession)

        # if timezone.now() > planned_time:
        if intervention_treatment_plan.nurse == user:
            TmpInterventionTreatmentPlanForWebsocket(intervention_treatment_plan=intervention_treatment_plan,
                                                     is_done=False, nurse=user, patient=patient).save()

    except ObjectDoesNotExist:
        intervention_treatment_plan = InterventionTreatmentPlan(treatment_plan_task=treatment_plan_task,
                                                                patient=User.objects.get(pk=patient_id),
                                                                planned_time=planned_time, profession=profession,
                                                                nurse=user)
        intervention_treatment_plan.save()
        TmpInterventionTreatmentPlanForWebsocket(intervention_treatment_plan=intervention_treatment_plan,
                                                 is_done=True, nurse=user, patient=patient).save()


# NEED CREATE TREATMENTPLAN AND THEN WE HAVE ONE
# NEED CHECK IF THERE IS A TREATMENTPLAN AND THEN DONT NEED TO ASK TO CREATE
# THEN SEND DATA TO TO treatmentplantask


def views_caregiver_treatment_plan_creation(request, patient_id, profession):
    if request.method == 'POST':
        plan = save_treatments_plan(patient_id)
        save_events_in_taskintreatmentplan(json.loads(request.body), plan)

    tasks = []
    # more draggables elements
    # mega table task
    for task in TaskLevel2.objects.filter(tasklevel1__profession=profession).distinct('id')[:5]:
        hours = task.duration.days * 24 + task.duration.seconds // 3600
        minutes = (task.duration.seconds % 3600) // 60
        data_event = f"'title': {task.name}, 'duration': {hours}:{minutes}"
        tasks.append({"id": task.id,
                      "name": task.name,
                      "svg_path": task.svg_path,
                      "data_event": json.dumps(list({data_event}))})

    target_date = datetime(year=2018, month=1, day=1, microsecond=0).astimezone(pytz.timezone(TIME_ZONE))
    events = get_events(patient_id, profession, target_date, 28)
    # events = get_events2(patient_id, profession)

    return render(request, 'app6_care/caregiver/treatments_plan_creation.html', {'patient_id': patient_id,
                                                                            'profession': profession,
                                                                            'user_language': USER_LANGUAGE,
                                                                            'tasks': tasks,
                                                                            'events': events})


def save_events_in_taskintreatmentplan(body, plan):
    print(f'voici d abord le body en entier avec tout les traitements envoyés : {body}')
    #first need to delete everything and save agin (in case we edit date for one treatment)
    TaskInTreatmentPlan.objects.filter(treatments_plan=plan).delete()
    for treatments in body:
        print(f'voici les traitements du body pour save : {treatments}')
        date = datetime.fromisoformat(treatments['start']).astimezone(pytz.timezone(TIME_ZONE))
        time_of_task = date.time()
        day_in_cycle = date.day
        task = TaskLevel2.objects.get(pk=treatments['id'])
        TaskInTreatmentPlan(treatments_plan=plan, task_level_2=task, day_in_cycle=day_in_cycle,
                            start_time=time_of_task).save()


def save_treatments_plan(patient_id):
    try:
        plan = TreatmentsPlan.objects.get(patient=User.objects.get(pk=patient_id))
        print('edit treatment')
    except ObjectDoesNotExist:
        next_monday = datetime.today() + timedelta(7 - datetime.today().weekday())
        TreatmentsPlan(patient=User.objects.get(pk=patient_id), start_date=next_monday).save()
        print('treatments plan created !')
        plan = TreatmentsPlan(patient=User.objects.get(pk=patient_id))
    return plan


def dlProtocol(request, protocol_id):
    protocol = Protocol_list.objects.get(id=protocol_id)
    return HttpResponse(protocol.file, content_type='application/pdf')


def plan_de_soin(request, patient_id):
    if request.method == 'POST':
        for day in range(8):
            if day > 0:
                TaskInTreatmentPlan(treatments_plan=TreatmentsPlan.objects.get(patient__pk=patient_id),
                                    day_in_cycle=day,
                                    start_time=request.POST['start_time'],
                                    task_level_2=TaskLevel2.objects.get(pk=request.POST['task_level_2'])).save()
    x = TreatmentsPlan.objects.filter(patient__id=patient_id)
    if not x:
        TreatmentsPlan(patient=User.objects.get(id=patient_id)).save()
    nb_of_task = {}
    for day in range(8):
        nb_of_task_per_day = TaskInTreatmentPlan.objects.filter(treatments_plan__patient__id=patient_id, day_in_cycle=day).count()
        if nb_of_task_per_day:
            nb_of_task[day] = nb_of_task_per_day
    today_day = datetime.today().weekday() + 1
    care_task_list = TaskLevel2.objects.order_by('name').all()
    context = {'patient_id': patient_id, 'nb_of_task': nb_of_task, 'today_day': today_day, 'range': range(8),
               'care_list': care_task_list}
    return render(request, 'app6_care/caregiver/plan_de_soin.html', context)


def plan_de_soin_jour(request, patient_id, day_id):
    care_task_list = TaskLevel1.objects.filter(need_for_intervention_plan=True, specific_to_a_resident=True).order_by('name')
    # json_of_tasks = get_json_of_tasks()
    # print(json_of_tasks)
    if request.method == 'POST':
        if request.POST.get('delete'):
            task_to_delete = TaskInTreatmentPlan.objects.get(pk=request.POST['delete'])
            task_to_delete.delete()
        else:
            TaskInTreatmentPlan(treatments_plan=TreatmentsPlan.objects.get(patient__pk=patient_id), day_in_cycle=request.POST['day_in_cycle'],
                                start_time=request.POST['start_time'], task_level_2=TaskLevel2.objects.get(pk=request.POST['task_level_2'])).save()
    context = {'patient_id': patient_id, 'day_id': day_id, 'care_list': care_task_list}
    tasks = TaskInTreatmentPlan.objects.filter(treatments_plan__patient__id=patient_id, day_in_cycle=day_id)
    tasks_list = []
    for task in tasks:
        tasks_list.append({
            'name': task.task_level_2.name,
            'time': task.start_time,
            'finished': check_if_task_is_done(task, User.objects.get(id=patient_id), day_id),
            'id': task.id
        })
    tasks_list.sort(key=lambda item: item['time'], reverse=False) #to order list esc by hour
    context['tasks_list'] = tasks_list

    return render(request, 'app6_care/caregiver/plan_de_soin_jour.html', context)


def check_if_task_is_done(task, user, day):
    today_day = datetime.today().weekday() + 1
    if today_day == day:
        x = Intervention.objects.filter(patient=user, details__task_level_2__name=task.task_level_2.name).last()
        if x:
            dt = datetime.now()
            print(f'x en entier {x}')
            print(f'uniquement le end de x {x.end}')
            if datetime(x.end.year, x.end.month, x.end.day) == datetime(dt.year, dt.month, dt.day):
                return True
            else:
                return False
        else:
            return False
    else:
        return 'no'


# def get_json_of_tasks():
#     tl1 = TaskLevel1.objects.filter(need_for_intervention_plan=True, specific_to_a_resident=True).order_by('name')
#     json = {}
#     for task1 in tl1:
#         if task1.details:
#             for task2 in task1.details.all():
#                 if task2.details:
#                     for task3 in task2.details.all():
#                         if task3.details:
#                             for task4 in task3.details.all():
#                                 json[task1.name][task2.name][task3.name] = task4.name
#                         else:
#                             json[task1.name][task2.name] = task3.name
#                 else:
#                     json[task1.name] = task2.name
#         else:
#             json[task1.name] = False
#     return json
