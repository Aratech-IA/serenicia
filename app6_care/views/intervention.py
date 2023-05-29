import pytz
import datetime
import itertools

from django.core.exceptions import ObjectDoesNotExist

from app9_personnalized_project.views import get_support_project_modal_data, get_story_life_modal_data
from projet.settings.settings import TIME_ZONE

from app1_base.models import User, Profile
from app6_care.models import TaskLevel1, TaskLevel2, TaskLevel3, TaskLevel4, Intervention, InterventionDetail, TaskComment, \
    Nappy, SectorNappy, FreeComment
from app6_care.forms.forms_intervention import TaskCommentForm
from app6_care.netsoins_api import post_intervention


def intervention(request, profession, specific_to_a_resident):
    context, tasks = {}, []
    intervention = intervention_details = None
    task_level = request.POST.get('task_level') if 'task_level' in request.POST else None
    task_id = int(request.POST.get('task_id')) if 'task_id' in request.POST else None
    task_to_comment_id = request.POST.get('task_to_comment_id') if \
        'task_to_comment_id' in request.POST and request.POST.get('task_to_comment_id') != 'None' else None
    task_to_comment = request.POST.get('task_to_comment') if \
        'task_to_comment' in request.POST and request.POST.get('task_to_comment') != 'False' else False
    context['cancel_mode'] = True if request.POST.get('toggle_cancel_mode') == 'False' or (
            request.POST.get('cancel_mode') == 'True' and 'toggle_cancel_mode' not in request.POST) else False
    context['comment_mode'] = True if request.POST.get('toggle_comment_mode') == 'False' or (
        request.POST.get('comment_mode') == 'True' and 'toggle_comment_mode' not in request.POST) else False
    task_comment_form = TaskCommentForm()

    if specific_to_a_resident:
        resident = User.objects.get(pk=request.session['resident_id'])
        profile = Profile.objects.get(user=resident)
        context['room_number'] = profile.client.room_number
        # to modify when Netsoins API returns us correct data
        opposite_gender = 'Man' if resident.profile.civility == 'Mme' else 'Woman' if resident.profile.civility == \
                                                                                      'M.' else None
    else:
        resident = None
        opposite_gender = None

    if request.method == 'POST':
        if request.POST.get('private_intervention') or request.POST.get('public_intervention') or \
                request.POST.get('punctual_treatment'):
            task_level = 1
            tasks = TaskLevel1.objects.filter(profession=profession, specific_to_a_resident=specific_to_a_resident)

        elif request.POST.get('delete'):
            Intervention.objects.get(pk=request.POST.get('delete')).delete()
            task_level = None

        elif request.POST.get('next-res') or request.POST.get('previous-res'):
            pass

        else:
            try:
                if request.POST.get('delete_confirmation'):
                    intervention_id = request.POST.get('delete_confirmation')
                    context['intervention_to_delete'] = Intervention.objects.get(pk=intervention_id)
                elif request.POST.get('continue'):
                    intervention_id = request.POST.get('continue')
                else:
                    intervention_id = request.POST.get('intervention_id')

                intervention = Intervention.objects.get(pk=intervention_id)
                details = Intervention.objects.get(pk=intervention_id).details.all()
                context['selected_tasks'] = [detail.task_level_2 for detail in details] + \
                                            [detail.task_level_3 for detail in details] + \
                                            [detail.task_level_4 for detail in details]

                if profession == 'AS':
                    context['selected_nappies'] = [detail.nappy for detail in details]

                if request.POST.get('done'):
                    intervention.end = datetime.datetime.now().astimezone(pytz.timezone(TIME_ZONE))
                    intervention.save()
                    task_level = None
                    if profession == 'AS':
                        # FUNCTION TO SEND TO API NETSOIN !!!
                        post_intervention(intervention)
                        decrement_nappy_stock(intervention)

                elif request.POST.get('confirm_comment'):
                    comment_a_task(request.POST, task_level, intervention, task_to_comment_id)
                    task_to_comment = False
                    context['comment_mode'] = False

                comments = TaskComment.objects.filter(intervention=intervention)
                context['commented_tasks'] = [comment.related_task_level_2 for comment in comments] + \
                                             [comment.related_task_level_3 for comment in comments] + \
                                             [comment.related_task_level_4 for comment in comments]
                intervention_details = InterventionDetail.objects.get(pk=request.POST.get('intervention_details_id'))

                if request.POST.get('toggle_cancel_mode') or request.POST.get('toggle_comment_mode'):

                    task_level, task_to_comment, tasks = toggle(request.POST, opposite_gender, task_level,
                                                                intervention_details, context, resident)

                elif request.POST.get('cancel_comment'):
                    context['comment_mode'] = False
                    task_to_comment = False

                elif context['cancel_mode']:
                    if request.POST.get('nappy_id'):
                        task_level = cancel_nappy(task_level, Nappy.objects.get(pk=request.POST.get('nappy_id')),
                                                  intervention_id, context, resident)
                    else:
                        task_level, tasks = cancel_task(request.POST.get('parent_task_level_3_id'), task_level, task_id,
                                                        opposite_gender, context, intervention_details, intervention_id)

                elif request.POST.get('nappy_id'):
                    task_level = select_nappy(task_level, context, request.POST.get('nappy_id'), intervention,
                                              intervention_details, resident,
                                              request.POST.get('parent_task_level_3_id'))

                # user clicked on a button at level 4
                elif task_level == '4':
                    if request.POST.get('get_back_to_task_level_3'):
                        if opposite_gender:
                            tasks = intervention_details.task_level_2.details.all().exclude(visible_by=opposite_gender)
                        else:
                            tasks = intervention_details.task_level_2.details.all()
                        task_level = 3

                    elif context['comment_mode']:
                        task_to_comment = TaskLevel4.objects.get(pk=task_id)
                        task_to_comment_id = task_id
                        task_level = 4

                    else:
                        if TaskLevel4.objects.get(pk=task_id) not in context['selected_tasks']:
                            context['selected_tasks'].append(TaskLevel4.objects.get(pk=task_id))
                            intervention_details = InterventionDetail.objects.create(
                                task_level_2=intervention_details.task_level_2,
                                task_level_3=intervention_details.task_level_3,
                                task_level_4=TaskLevel4.objects.get(pk=task_id))
                            intervention.details.add(intervention_details)

                        task_level = 4
                        tasks = TaskLevel3.objects.get(pk=request.POST.get('parent_task_level_3_id')).details.all()
                        context['parent_task_level_3_id'] = request.POST.get('parent_task_level_3_id')

                # user clicked on a button at level 3
                elif task_level == '3':
                    if context['comment_mode']:
                        task_to_comment = TaskLevel3.objects.get(pk=task_id)
                        task_to_comment_id = task_id
                        task_level = 3

                    else:
                        if TaskLevel3.objects.get(pk=task_id) not in context['selected_tasks']:
                            context['selected_tasks'].append(TaskLevel3.objects.get(pk=task_id))
                            intervention_details = InterventionDetail.objects.create(
                                task_level_2=intervention_details.task_level_2,
                                task_level_3=TaskLevel3.objects.get(pk=task_id))
                            intervention.details.add(intervention_details)

                        context['parent_task_level_3_id'] = task_id

                        if TaskLevel3.objects.get(pk=task_id).details.all():
                            if opposite_gender:
                                tasks = TaskLevel3.objects.get(pk=task_id).details.all().exclude(visible_by=opposite_gender)
                            else:
                                tasks = TaskLevel3.objects.get(pk=task_id).details.all()
                            task_level = 4
                        else:
                            if TaskLevel3.objects.get(pk=task_id).nappy.all():
                                context['nappies_related_to_resident'] = Nappy.objects.filter(usernappy__user=resident)
                                task_level = 4
                            else:
                                task_level = 3
                                tasks = intervention_details.task_level_2.details.all()

            except ValueError:
                # user clicked on a button at level 2
                if task_level == '2':
                    if request.POST.get('toggle_cancel_mode') or request.POST.get('toggle_comment_mode'):
                        task_level = 2
                        task_to_comment = False

                    elif context['cancel_mode']:
                        task_level = cancel_task(request.POST.get('parent_task_level_3_id'), task_level, task_id,
                                                 opposite_gender, context, intervention_details, intervention_id)

                    elif context['comment_mode']:
                        task_level = 2
                        if 'cancel_comment' in request.POST:
                            context['comment_mode'] = False
                            task_to_comment = False
                        else:
                            task_to_comment = TaskLevel2.objects.get(pk=task_id)
                            task_to_comment_id = task_id

                    elif request.POST.get('confirm_comment'):
                        task_level = 2

                    else:
                        selected_task = TaskLevel2.objects.get(pk=task_id)
                        intervention_details = InterventionDetail.objects.create(task_level_2=selected_task)
                        intervention.details.add(intervention_details)
                        context['selected_tasks'].append(selected_task)
                        if intervention_details.task_level_2.details.all():
                            if opposite_gender:
                                tasks = intervention_details.task_level_2.details.all().exclude(visible_by=opposite_gender)
                            else:
                                tasks = intervention_details.task_level_2.details.all()
                            task_level = 3
                        else:
                            if selected_task.nappy.all():
                                context['nappies_related_to_resident'] = Nappy.objects.filter(usernappy__user=resident)

                                task_level = 3
                            else:
                                task_level = 2
                            # task_level = 2

                # user choosed a category at level 1
                if task_level == '1':
                    intervention = Intervention.objects.create(
                        nurse=request.user, patient=resident, type=TaskLevel1.objects.get(pk=task_id),
                        profession=profession, specific_to_a_resident=specific_to_a_resident)
                    task_level = 2

            except ObjectDoesNotExist:
                task_level = 2

    if (task_level == 2 or request.POST.get('get_back_to_task_level_2')) and not task_to_comment:
        if opposite_gender:
            tasks = intervention.type.details.all().exclude(visible_by=opposite_gender)
        else:
            tasks = intervention.type.details.all()

    elif task_level == 1:
        tasks = TaskLevel1.objects.filter(profession=profession, specific_to_a_resident=specific_to_a_resident)

    incomplete_interventions = Intervention.objects.order_by('-start').filter(nurse=request.user, patient=resident,
                                                                              end=None, profession=profession,
                                                                              from_care_plan=False)

    context['incomplete_interventions'] = incomplete_interventions if incomplete_interventions and task_level is None \
        else None

    # tasks related to nappy appear only if resident wears nappy :
    if profession == 'AS' and not Nappy.objects.filter(usernappy__user=resident):
        tasks = list(itertools.filterfalse(lambda task: bool(task.nappy.all()), tasks))

    context['tasks'] = tasks
    context['task_level'] = task_level
    context['intervention'] = intervention if intervention else None
    context['intervention_details'] = intervention_details if intervention_details and task_level != 2 else None
    context['no_selected_tasks'] = True if len(
        InterventionDetail.objects.filter(intervention=intervention)) == 0 else False
    context['task_to_comment'] = task_to_comment
    context['task_to_comment_id'] = task_to_comment_id
    context['task_comment_form'] = task_comment_form
    context['specific_to_a_resident'] = specific_to_a_resident
    if resident:
        context.update({'support_project': get_support_project_modal_data(resident.profileserenicia),
                        'story_life': get_story_life_modal_data(resident.profileserenicia)})
        context['free_comments'] = get_last_ten_free_comment(resident)

    return context


def select_nappy(task_level, context, nappy_id, intervention, intervention_details, resident, parent_task_level_3_id):
    selected_nappy = Nappy.objects.get(pk=nappy_id)
    context['nappies_related_to_resident'] = Nappy.objects.filter(usernappy__user=resident)

    if task_level == '3':
        if selected_nappy not in context['selected_nappies']:
            context['selected_nappies'].append(selected_nappy)
            intervention_details = InterventionDetail.objects.create(
                task_level_2=intervention_details.task_level_2,
                nappy=selected_nappy)
            intervention.details.add(intervention_details)
            intervention_details.nappy = selected_nappy
        return 3

    if task_level == '4':
        if selected_nappy not in context['selected_nappies']:
            context['selected_nappies'].append(selected_nappy)
            intervention_details = InterventionDetail.objects.create(
                task_level_2=intervention_details.task_level_2,
                task_level_3=TaskLevel3.objects.get(pk=parent_task_level_3_id),
                nappy=selected_nappy)
            intervention.details.add(intervention_details)
            intervention_details.nappy = selected_nappy
            context['parent_task_level_3_id'] = parent_task_level_3_id
        return 4


def cancel_nappy(task_level, selected_nappy, intervention_id, context, resident):
    context['nappies_related_to_resident'] = Nappy.objects.filter(usernappy__user=resident)
    if selected_nappy in context['selected_nappies']:
        context['selected_nappies'].remove(selected_nappy)
        detail_to_cancel = InterventionDetail.objects.get(nappy=selected_nappy, intervention__pk=intervention_id)
        detail_to_cancel.nappy = None
        detail_to_cancel.save()

    if task_level == '4':
        return 4

    if task_level == '3':
        return 3


def cancel_task(parent_task_level_3_id, task_level, task_id, opposite_gender, context, intervention_details,
                intervention_id):
    if task_level == '4':
        context['parent_task_level_3_id'] = parent_task_level_3_id

        if opposite_gender:
            tasks = TaskLevel3.objects.get(pk=parent_task_level_3_id).details.all().exclude(visible_by=opposite_gender)
        else:
            tasks = TaskLevel3.objects.get(pk=parent_task_level_3_id).details.all()

        if TaskLevel4.objects.get(pk=task_id) in context['selected_tasks']:
            detail_to_cancel = InterventionDetail.objects.get(task_level_4=TaskLevel4.objects.get(pk=task_id),
                                                              intervention__pk=intervention_id)
            detail_to_cancel.task_level_4 = None
            detail_to_cancel.save()
            context['selected_tasks'].remove(TaskLevel4.objects.get(pk=task_id))

        return 4, tasks

    if task_level == '3':
        if opposite_gender:
            tasks = intervention_details.task_level_2.details.all().exclude(visible_by=opposite_gender)
        else:
            tasks = intervention_details.task_level_2.details.all()

        if TaskLevel3.objects.get(pk=task_id) in context['selected_tasks']:
            intervention_details_to_cancel = InterventionDetail.objects.filter(
                task_level_3=TaskLevel3.objects.get(pk=task_id), intervention__pk=intervention_id)
            for detail_to_cancel in intervention_details_to_cancel:
                detail_to_cancel.task_level_3 = detail_to_cancel.task_level_4 = None
                detail_to_cancel.save()
            context['selected_tasks'] = [detail.task_level_3 for detail in
                                         Intervention.objects.get(pk=intervention_id).details.all()]

        return 3, tasks

    if task_level == '2':
        if TaskLevel2.objects.get(pk=task_id) in context['selected_tasks']:
            InterventionDetail.objects.filter(task_level_2=TaskLevel2.objects.get(pk=task_id),
                                              intervention__pk=intervention_id).all().delete()
            context['selected_tasks'] = [detail.task_level_2 for detail in
                                         Intervention.objects.get(pk=intervention_id).details.all()]

        return 2


def comment_a_task(request_post, task_level, intervention, task_to_comment_id):
    task_comment_form = TaskCommentForm(request_post)
    if task_comment_form.is_valid():
        intervention_comment = task_comment_form.cleaned_data['content']
        if task_level == '4':
            comment = TaskComment.objects.create(
                content=intervention_comment, related_task_level_4=TaskLevel4.objects.get(pk=task_to_comment_id))
        elif task_level == '3':
            comment = TaskComment.objects.create(
                content=intervention_comment, related_task_level_3=TaskLevel3.objects.get(pk=task_to_comment_id))
        elif task_level == '2':
            comment = TaskComment.objects.create(
                content=intervention_comment, related_task_level_2=TaskLevel2.objects.get(pk=task_to_comment_id))
        comment.save()
        intervention.task_comment.add(comment)


def toggle(request_post, opposite_gender, task_level, intervention_details, context, resident):
    if task_level == '4':
        context['parent_task_level_3_id'] = request_post.get('parent_task_level_3_id')
        parent_task_level_3 = TaskLevel3.objects.get(pk=request_post.get('parent_task_level_3_id'))
        if parent_task_level_3.nappy.all():
            context['nappies_related_to_resident'] = Nappy.objects.filter(usernappy__user=resident)
            # print(request_post.get('parent_task_level_3_id'))
            return 4, False, None

        if opposite_gender:
            tasks = parent_task_level_3.details.all().details.all().exclude(visible_by=opposite_gender)
        else:
            tasks = parent_task_level_3.details.all()

        return 4, False, tasks

    if task_level == '3':
        if intervention_details.task_level_2.nappy.all():
            context['nappies_related_to_resident'] = Nappy.objects.filter(usernappy__user=resident)
            return 3, False, None

        if opposite_gender:
            tasks = intervention_details.task_level_2.details.all().exclude(visible_by=opposite_gender)
        else:
            tasks = intervention_details.task_level_2.details.all()

        return 3, False, tasks


def decrement_nappy_stock(intervention):
    def decrement(nappy):
        sector_nappy = SectorNappy.objects.get(nappy=nappy, sector=intervention.patient.profile.client.sector)
        if sector_nappy.stock > 0:
            sector_nappy.stock -= 1
            sector_nappy.save()
        elif nappy.stock_in_storehouse > 0:
            nappy.stock_in_storehouse -= 1
            nappy.save()
    [decrement(detail.nappy) for detail in InterventionDetail.objects.filter(intervention=intervention) if detail.nappy]


def get_last_ten_free_comment(resident):
    last_ten_comment = FreeComment.objects.filter(patient=resident).order_by('-start')[:10]
    return last_ten_comment
