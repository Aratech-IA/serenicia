from datetime import datetime

from dateutil.relativedelta import relativedelta
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponseServerError, JsonResponse, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from app4_ehpad_base.models import ProfileSerenicia
from .models import PlanningEvent, Event


def calendar_configuration(display='month', change_view=True, editable=False, events=PlanningEvent.objects.all()):
    display_options = {'month': 'dayGridMonth', 'week': 'timeGridWeek'}
    editable_options = {True: 'true', False: 'false'}
    return {'events': list(events), 'editable': editable_options[editable],
            'view': display_options[display], 'change_view': change_view}


def update_event(request, pl_event_id, start, end):
    start = timezone.make_aware(datetime.strptime(start.split('.')[0], '%Y-%m-%dT%H:%M:%S'), timezone=timezone.utc)
    end = timezone.make_aware(datetime.strptime(end.split('.')[0], '%Y-%m-%dT%H:%M:%S'), timezone=timezone.utc)
    try:
        PlanningEvent.objects.filter(id=pl_event_id).update(start=start, end=end)
    except ObjectDoesNotExist:
        return HttpResponseServerError()
    return JsonResponse('ok', safe=False)


def get_event_details(request, pl_event_id, editable):
    def custom_date_displaying(date):
        aware_date = timezone.localtime(date)
        day = _(aware_date.strftime('%A'))
        month = _(aware_date.strftime('%B'))
        return f'{day} {aware_date.strftime("%-d")} {month} {aware_date.strftime("%Y - %H:%M")}'

    def custom_date_input(date):
        aware_date = timezone.localtime(date)
        return f"{aware_date.isoformat().split('.')[0][:-3]}"

    pl_event = PlanningEvent.objects.filter(id=pl_event_id)
    if not pl_event.exists():
        return HttpResponseServerError()
    data = pl_event.values('event__type', 'start', 'end').get()
    result = {'title': data['event__type']}
    if editable == 'true':
        result.update({'start': custom_date_input(data['start']), 'end': custom_date_input(data['end'])})
    else:
        result.update({'start': custom_date_displaying(data['start']), 'end': custom_date_displaying(data['end'])})
    pl_event = pl_event.get()
    if pl_event.event.is_activity:
        if request.user.has_perm('app0_access.view_animation'):
            result['details_url'] = reverse('app10_social_activities historic details', kwargs={'act_id': pl_event_id})
        elif pl_event.blog_post:
            result['details_url'] = reverse('show_post', kwargs={'post_id': pl_event.blog_post.id})
    return JsonResponse(result, safe=False)


def delete_event(request, pl_event_id):
    PlanningEvent.objects.filter(id=pl_event_id).delete()
    return HttpResponse(status=200)


def calendar_day_view(request, year, month, day):
    try:
        resident = ProfileSerenicia.objects.get(user__id=request.session['resident_id'])
    except (ObjectDoesNotExist, AttributeError):
        return redirect('app4_ehpad_base index')
    month += 1
    if month < 10:
        month = f"0{month}"
    if day < 10:
        day = f"0{day}"
    events = list(PlanningEvent.objects.filter(participants=resident))
    events.extend(get_birthday_events(resident, request.user.profileserenicia))
    return render(request, 'app15_calendar/calendar_widget_day.html', {'events': events, 'initial': f"{year}-{month}-{day}"})


def get_birthday_events(resident, connected):
    def get_bday(date):
        bday = timezone.make_aware(datetime(year=timezone.now().year, month=date.month,
                                            day=date.day))
        return bday, bday + relativedelta(years=+1)

    if resident == connected:
        ev_type_str = _('Happy birthday') + ' !'
    else:
        ev_type_str = f'{_("Birthday of")} {resident.user.profile.civility} {resident.user.first_name[0]}' \
                      f' {resident.user.last_name}'
    try:
        bday_now, bday_next = get_bday(resident.birth_date)
        result = [PlanningEvent(event=Event(type=ev_type_str, is_birthday=True, organizer=resident),
                                start=bday_now),
                  PlanningEvent(event=Event(type=ev_type_str, is_birthday=True, organizer=resident),
                                start=bday_next)
                  ]
    except AttributeError:
        result = []
    for profj in ProfileSerenicia.objects.filter(user_list=resident.user.profile,
                                                 user__groups__permissions__codename='view_family',
                                                 birth_date__isnull=False):
        if profj == connected:
            type_str = _('Happy birthday') + ' !'
        else:
            type_str = _('Birthday of') + ' ' + profj.user.first_name + ' ' + profj.user.last_name
        bday_now, bday_next = get_bday(profj.birth_date)
        result.append(PlanningEvent(event=Event(type=type_str, is_birthday=True, organizer=profj),
                                    start=bday_now))
        result.append(PlanningEvent(event=Event(type=type_str, is_birthday=True, organizer=profj),
                                    start=bday_next))
    return result
