from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.http import JsonResponse, HttpResponseServerError
from django.shortcuts import render, redirect
from django.utils import timezone
from django.utils.timezone import get_current_timezone
from django.utils.translation import gettext_lazy as _
from datetime import datetime, timedelta

from app4_ehpad_base.models import ProfileSerenicia
from app15_calendar.models import PlanningEvent
from app6_care.models import TaskLevel1, CarePlan, TaskLevel2, CarePlanEvent, TaskLevel3, Intervention, InterventionDetail, \
    TaskLevel4, TaskComment


# ----------------------------------------------------------------------------------------------------------------------
#                                                  CARE PLAN USE
# ----------------------------------------------------------------------------------------------------------------------
def get_tasks_by_date(plan, date):
    # nombre de répétition d'un même jour dans le plan de soins = nombre de semaines dans un cycle
    weekday_cycles = plan.tasks.filter(planning_event_new__start__iso_week_day=date.isoweekday()).distinct(
        'planning_event_new__start__date').order_by('planning_event_new__start__date')
    try:
        # nombre de semaines écoulées depuis le premier cycle
        weeks_delta = int((date - weekday_cycles.first().planning_event_new.start).days / 7)
        # modulo du nombre de répétitions du cycle, renvoi le numéro de la semaine en cours en base 0
        index = weeks_delta % weekday_cycles.count()
    except (ZeroDivisionError, AttributeError):
        # pas de soins programmés ce jour
        raise ObjectDoesNotExist
    # récupère les taches du plan de soins du jour à la semaine du cycle
    tasks_date = weekday_cycles[index].planning_event_new.start.astimezone(get_current_timezone())
    return plan.tasks.filter(planning_event_new__start__date=tasks_date.date())


@login_required
@permission_required('app0_access.view_care')
def care_plan(request):
    reject = TaskLevel3.objects.get(reject=True)

    def create_sub_level_dict(data, intervention):
        sub_lvl = {'lvl2': data.task_lvl_2, 'date': data.planning_event_new.start, 'done': False}
        if intervention.exists():
            intervention = intervention.get()
            sub_lvl['rejected'] = intervention.details.filter(task_level_3=reject,
                                                              task_level_2=data.task_lvl_2).exists()
        if data.task_lvl_3:
            sub_lvl['lvl3'] = data.task_lvl_3
            sub_lvl['details'] = data.task_lvl_3.details.exists()
            try:
                if intervention.details.filter(task_level_2=data.task_lvl_2,
                                               task_level_3=data.task_lvl_3).exists():
                    sub_lvl['done'] = intervention.details.filter(task_level_2=data.task_lvl_2,
                                                                  task_level_3=data.task_lvl_3).first().id
                sub_lvl['details_done'] = [detail.task_level_4 for detail in intervention.details.filter(
                    task_level_4__in=data.task_lvl_3.details.all(), task_level_2=data.task_lvl_2,
                    task_level_3=data.task_lvl_3)]
                sub_lvl['comment'] = intervention.task_comment.get(related_task_level_2=data.task_lvl_2,
                                                                   related_task_level_3=data.task_lvl_3)
            except (AttributeError, ObjectDoesNotExist):
                pass
        else:
            sub_lvl['details'] = data.task_lvl_2.details.exists()
            try:
                if intervention.details.filter(task_level_2=data.task_lvl_2).exists():
                    sub_lvl['done'] = intervention.details.filter(task_level_2=data.task_lvl_2).first().id
                sub_lvl['details_done'] = [detail.task_level_3 for detail in intervention.details.filter(
                    task_level_3__in=data.task_lvl_2.details.all(), task_level_2=data.task_lvl_2)]
                sub_lvl['comment'] = intervention.task_comment.get(related_task_level_2=data.task_lvl_2)
            except (AttributeError, ObjectDoesNotExist):
                pass
            if data.task_lvl_2.details.filter(id=reject.id).exists():
                sub_lvl['reject'] = reject.id
        if not sub_lvl['done'] and inter_done:
            sub_lvl['unrealized'] = True
        return sub_lvl

    date = timezone.now()
    try:
        resident = ProfileSerenicia.objects.get(user__id=request.session['resident_id'])
        plan = CarePlan.objects.get(resident=resident)
        todays_tasks = get_tasks_by_date(plan, date)
    except ObjectDoesNotExist:
        return redirect('caregiver')
    list_lvl1 = todays_tasks.distinct('task_lvl_1').values('task_lvl_1__id', 'task_lvl_1__color')
    todays_tasks = todays_tasks.order_by('planning_event_new__start')
    first_task = todays_tasks.first()
    result = []
    inter = Intervention.objects.filter(nurse=request.user, patient=User.objects.get(id=request.session['resident_id']),
                                        from_care_plan=True, start__date=date.date())
    inter_done = inter.filter(type=first_task.task_lvl_1, lvl1_inter_id=first_task.lvl1_inter_id,
                              end__isnull=False).exists()
    tmp_dict = {'lvl1': first_task.task_lvl_1, 'date': first_task.planning_event_new.start,
                'sub_lvl': [create_sub_level_dict(first_task, inter.filter(type=first_task.task_lvl_1,
                                                                           lvl1_inter_id=first_task.lvl1_inter_id))],
                'lvl1_inter_id': first_task.lvl1_inter_id,
                'done': inter_done}
    for task in todays_tasks[1:]:
        if tmp_dict.get('lvl1') != task.task_lvl_1 or tmp_dict.get('lvl1_inter_id') != task.lvl1_inter_id:
            # nouveau lvl1, ajout lvl1 en cours puis création nouveau ou même lvl1 mais autre intervention
            result.append(tmp_dict.copy())
            inter_done = inter.filter(type=task.task_lvl_1, lvl1_inter_id=task.lvl1_inter_id,
                                      end__isnull=False).exists()
            tmp_dict.update({'lvl1': task.task_lvl_1, 'date': task.planning_event_new.start,
                             'sub_lvl': [create_sub_level_dict(task, inter.filter(type=task.task_lvl_1,
                                                                                  lvl1_inter_id=task.lvl1_inter_id))],
                             'lvl1_inter_id': task.lvl1_inter_id,
                             'done': inter_done})
        else:
            # ajout sub_lvl de la tache de lvl1 en cours
            tmp_dict['sub_lvl'].append(create_sub_level_dict(task, inter.filter(type=task.task_lvl_1,
                                                                                lvl1_inter_id=task.lvl1_inter_id)))
    result.append(tmp_dict)
    return render(request, 'app6_care/caregiver/care_plan.html', {"tasks": result, 'tlvl1': list_lvl1, 'today': True,
                                                             'resident': resident})


def care_plan_intervention(request, lvl1, lvl1_inter_id, lvl2, lvl3, lvl4):
    try:
        inter = Intervention.objects.get_or_create(type=TaskLevel1.objects.get(id=lvl1), nurse=request.user,
                                                   patient=User.objects.get(id=request.session['resident_id']),
                                                   from_care_plan=True, start__date=timezone.now().date(),
                                                   lvl1_inter_id=lvl1_inter_id)[0]
    except (ObjectDoesNotExist, AttributeError):
        return JsonResponse('error', safe=False)
    task_lvl2 = TaskLevel2.objects.get(id=lvl2)
    if lvl4:
        task_lvl4 = TaskLevel4.objects.get(id=lvl4)
        task_lvl3 = TaskLevel3.objects.get(id=lvl3)
        try:
            inter_detail = inter.details.get(task_level_2=task_lvl2, task_level_3=task_lvl3, task_level_4=task_lvl4)
        except ObjectDoesNotExist:
            inter_detail = InterventionDetail.objects.create(task_level_2=task_lvl2, task_level_3=task_lvl3,
                                                             task_level_4=task_lvl4)
            inter.details.add(inter_detail)
    elif lvl3:
        task_lvl3 = TaskLevel3.objects.get(id=lvl3)
        try:
            inter_detail = inter.details.get(task_level_2=task_lvl2, task_level_3=task_lvl3)
        except ObjectDoesNotExist:
            inter_detail = InterventionDetail.objects.create(task_level_2=task_lvl2, task_level_3=task_lvl3)
            inter.details.add(inter_detail)
    else:
        try:
            inter_detail = inter.details.get(task_level_2=task_lvl2)
        except ObjectDoesNotExist:
            inter_detail = InterventionDetail.objects.create(task_level_2=task_lvl2)
            inter.details.add(inter_detail)
    return JsonResponse({'detail_id': inter_detail.id})


def care_plan_cancel(request, detail_id):
    InterventionDetail.objects.filter(id=detail_id).delete()
    return JsonResponse({'detail_id': detail_id})


def finalize_intervention(request, lvl1, lvl1_inter_id):
    try:
        inter = Intervention.objects.get_or_create(type=TaskLevel1.objects.get(id=lvl1), nurse=request.user,
                                                   patient=User.objects.get(id=request.session['resident_id']),
                                                   from_care_plan=True,
                                                   start__date=timezone.now().date(), lvl1_inter_id=lvl1_inter_id)[0]
        inter.end = timezone.now()
        inter.save()
        return JsonResponse({'detail_id': True})
    except (ObjectDoesNotExist, AttributeError):
        return JsonResponse('error', safe=False)


def add_comment(request, lvl1, lvl1_inter_id, lvl2, lvl3, comment):
    try:
        inter = Intervention.objects.get_or_create(type=TaskLevel1.objects.get(id=lvl1), nurse=request.user,
                                                   patient=User.objects.get(id=request.session['resident_id']),
                                                   from_care_plan=True,
                                                   start__date=timezone.now().date(), lvl1_inter_id=lvl1_inter_id)[0]
    except ObjectDoesNotExist:
        return JsonResponse('error', safe=False)
    if lvl3:
        try:
            task_comment = inter.task_comment.get(related_task_level_2=lvl2, related_task_level_3=lvl3)
        except ObjectDoesNotExist:
            task_comment = TaskComment.objects.create(related_task_level_2=TaskLevel2.objects.get(id=lvl2),
                                                      related_task_level_3=TaskLevel3.objects.get(id=lvl3))
    else:
        try:
            task_comment = inter.task_comment.get(related_task_level_2=lvl2)
        except ObjectDoesNotExist:
            task_comment = TaskComment.objects.create(related_task_level_2=TaskLevel2.objects.get(id=lvl2))
    task_comment.content = comment
    task_comment.save()
    inter.task_comment.add(task_comment)
    return JsonResponse({'detail_id': task_comment.id})


def delete_comment(request, com_id):
    TaskComment.objects.filter(id=com_id).delete()
    return JsonResponse({'detail_id': com_id})


# ----------------------------------------------------------------------------------------------------------------------
#                                                CARE PLAN MANAGEMENT
# ----------------------------------------------------------------------------------------------------------------------
@login_required
@permission_required('app0_access.view_care')
def care_plan_creation(request):
    try:
        profilej = ProfileSerenicia.objects.get(user__id=request.session.get('resident_id'))
    except ObjectDoesNotExist:
        return redirect('app4_ehpad_base index')
    plan, is_created = CarePlan.objects.get_or_create(resident=profilej)
    first_event = plan.tasks.order_by("planning_event_new__start").first()
    if first_event:
        first_date = first_event.planning_event_new.start.astimezone(get_current_timezone())
    else:
        first_date = timezone.now()
    initial_week = int(request.POST.get('week', 1))
    first_monday = first_date - timedelta(days=first_date.weekday())
    initial_date = first_monday + timedelta(weeks=initial_week - 1)
    if request.method == 'POST':
        if request.POST.get('day'):
            date = (initial_date + timedelta(days=int(request.POST.get('day')))).date()
            plan.tasks.filter(planning_event_new__start__date=date).delete()
        else:
            for task in plan.tasks.filter(planning_event_new__start__gte=initial_date,
                                          planning_event_new__start__lt=initial_date + timedelta(weeks=1)):
                pl_ev = task.planning_event_new
                pl_ev.pk = None
                pl_ev.start = pl_ev.start + timedelta(weeks=1)
                pl_ev.end = pl_ev.end + timedelta(weeks=1)
                pl_ev.save()
                task.pk = None
                task.planning_event_new = pl_ev
                task.save()
                plan.tasks.add(task)
        return redirect('care plan creation')
    task_list = TaskLevel1.objects.filter(details__care_plan=True).distinct('name').order_by('name')
    return render(request, 'app6_care/caregiver/care_plan_creation.html', {'task_list': task_list, 'editable': 'true',
                                                                      'plan': plan, 'first_monday': first_monday,
                                                                      'week': initial_week,
                                                                      'initial_date': initial_date})


def change_task_color(request, task_id, color):
    TaskLevel1.objects.filter(id=task_id).update(color="#" + color)
    return JsonResponse('ok', safe=False)


def get_lvl1_inter_id(event, plan):
    lvl1_tasks = plan.tasks.filter(task_lvl_1=event.task_lvl_1).order_by('planning_event_new__start').exclude(id=event.id)
    if not lvl1_tasks.exists():
        return 1
    previous_task = lvl1_tasks.filter(planning_event_new__start__lte=event.planning_event_new.start).last()
    if previous_task and previous_task.planning_event_new.start >= (event.planning_event_new.start - timedelta(minutes=30)):
        return previous_task.lvl1_inter_id
    next_task = lvl1_tasks.filter(planning_event_new__start__gte=event.planning_event_new.start).first()
    if next_task and next_task.planning_event_new.start <= (event.planning_event_new.start + timedelta(minutes=30)):
        return next_task.lvl1_inter_id
    return lvl1_tasks.order_by('lvl1_inter_id').last().lvl1_inter_id + 1


def create_event(request):
    try:
        plan = CarePlan.objects.get_or_create(resident__user__id=request.session.get('resident_id'))[0]
    except ObjectDoesNotExist:
        return JsonResponse('error', safe=False)
    if request.method == 'POST':
        start = timezone.make_aware(datetime.fromisoformat(request.POST.get('start')), timezone=timezone.utc)
        planning_event = PlanningEvent.objects.create(start=start, end=start + timedelta(minutes=30))
        care_ev = CarePlanEvent.objects.create(planning_event_new=planning_event,
                                               task_lvl_1=TaskLevel1.objects.get(id=request.POST.get('lvl1')),
                                               task_lvl_2=TaskLevel2.objects.get(id=request.POST.get('lvl2')))
        plan.tasks.add(care_ev)
        if request.POST.get('lvl3') != 'undefined':
            CarePlanEvent.objects.filter(id=care_ev.id).update(
                task_lvl_3=TaskLevel3.objects.get(id=request.POST.get('lvl3')))
        CarePlanEvent.objects.filter(id=care_ev.id).update(lvl1_inter_id=get_lvl1_inter_id(care_ev, plan))
        return JsonResponse(planning_event.id, safe=False)


def delete_event(request, pl_event_id):
    result = PlanningEvent.objects.filter(id=pl_event_id).delete()
    return JsonResponse(result, safe=False)


def update_event(request, pl_event_id, start):
    start = timezone.make_aware(datetime.strptime(start.split('.')[0], '%Y-%m-%dT%H:%M:%S'), timezone=timezone.utc)
    try:
        PlanningEvent.objects.filter(id=pl_event_id).update(start=start, end=start + timedelta(minutes=30))
    except ObjectDoesNotExist:
        return HttpResponseServerError()
    care_ev = CarePlanEvent.objects.get(planning_event_new__id=pl_event_id)
    plan = CarePlan.objects.get(tasks=care_ev)
    CarePlanEvent.objects.filter(id=care_ev.id).update(lvl1_inter_id=get_lvl1_inter_id(care_ev, plan))
    return JsonResponse('ok', safe=False)


def show_event(request, pl_ev_id):
    pl_event = PlanningEvent.objects.filter(id=pl_ev_id)
    if not pl_event.exists():
        return HttpResponseServerError()
    care_event = CarePlanEvent.objects.get(planning_event_new=pl_event.get())
    localdate = timezone.localtime(care_event.planning_event_new.start)
    day = _(localdate.strftime('%A'))
    result = {'lvl1': care_event.task_lvl_1.name, 'lvl2': care_event.task_lvl_2.name,
              'date': f'{day} {localdate.strftime("%H:%M")}',
              'color': care_event.task_lvl_1.color}
    if care_event.task_lvl_3:
        result['lvl3'] = care_event.task_lvl_3.name
    return JsonResponse(result, safe=False)
