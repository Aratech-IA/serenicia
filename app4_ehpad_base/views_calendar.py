# -*- coding: utf-8 -*-
"""
Created on Sun Apr 14 21:29:53 2019
"""
from datetime import timedelta
from .forms import SocialPlanningEventsForm
from app1_base.log import Logger
import app4_ehpad_base.api_google as gc_api
from .models import WeekRoutine, get_time_choices, ProfileSerenicia
from app15_calendar.models import Event, PlanningEvent
import logging
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

if 'log_calendar' not in globals():
    global log_calendar
    log_calendar = Logger('calendar', level=logging.ERROR, file=False).run()


def update_planning(request):
    message = {}
    if request.method == 'POST':
        resident = ProfileSerenicia.objects.get(user__id=request.session['resident_id'])
        if request.POST.get('deleting_event'):
            cancel_event(request.POST.get('deleting_event'), resident)
            message = {'message': _('Event successfully deleted.'), 'category': _('Delete event')}
        else:
            planning_event = SocialPlanningEventsForm(request.POST)
            if planning_event.is_valid():
                instance, event_type = planning_event.save(commit=False)
                organizer = request.user.profileserenicia
                if check_event(instance, organizer, resident):  # check if there is not an event on the same time
                    event = Event.objects.create(type=event_type, organizer=organizer)
                    instance.event = event
                    instance.save()
                    instance.participants.add(resident, resident)
                    gg_event = update_google_calendar(instance, resident)
                    try:
                        instance.gg_event_id = gg_event.get('id')
                    except AttributeError:  # in case google doesn't respond, we need to continue anyway
                        pass
                    message = {'message': _('Event successfully added !'), 'category': _('Add event')}
                else:
                    message = {'message': _('Date already full'), 'category': _('Can not add event')}
    new_event = SocialPlanningEventsForm()
    return new_event, message


def check_event(event, organizer, participants):
    social_events = PlanningEvent.objects.filter(start__gte=event.start,
                                                 event__organizer=organizer,
                                                 participants=participants)
    log_calendar.debug(f"check start :{event.start}  / check end : "
                       f"{event.end}")
    for e in social_events:
        log_calendar.debug(f"event start :{e.start}  / event end : {e.end}")
        log_calendar.debug(f"event start :{e.start}  / event end : {e.end}")
        check1 = event.start < e.end  # event start before end
        check2 = event.end > e.start  # end after start
        if check1 and check2:
            return False
    return True


def display_planning(request):
    """returns to the social_planning.html page all pertinent data to refresh the custom calendar
    via a dicts' dict : slots_colors whose each sub dict is a day listing the color of each 30minutes"""
    day_delta = 9
    planning = {}
    resident = ProfileSerenicia.objects.get(user__id=request.session['resident_id'])
    times_choices = get_time_choices()
    times_dict = dict([(idx, i) for idx, i in enumerate(get_time_choices())])
    for i in range(day_delta):
        day = timezone.localtime() + timedelta(days=i)
        log_calendar.debug(f"day is :{day}  ")
        day_events = PlanningEvent.objects.filter(start__date=day.date(), participants=resident)
        # get the routines for the day
        routines = WeekRoutine.objects.filter(day=day.weekday()) | WeekRoutine.objects.filter(day=10)
        # get all the events on the planning for the day
        event = []
        routine = []
        log_calendar.debug(f"day event :{day_events}")
        log_calendar.debug(f"time choices :{times_choices}")
        for idx, t0 in enumerate(times_choices):
            t1 = times_choices[(idx + 1) % len(times_choices)].replace(day.year, day.month, day.day)
            t0 = t0.replace(day.year, day.month, day.day)
            event.append([i for i in day_events if i.start < t1 and i.end > t0])
            routine.append([i.routine.name for i in routines if i.routine.start <= idx < i.routine.end])
        # remove last  slot because of presentation constraint
        event.pop()
        routine.pop()
        # make the planning for day_delta  days
        planning[day.date()] = zip(event, routine)
    event_data = {'hours': times_choices[0::2], 'planning': planning, 'cal_id': resident.cal_id,
                  'cancellables': cancellables(request.user, resident)}
    return event_data


def cancellables(user, resident):
    result = PlanningEvent.objects.filter(event__organizer__user=user,
                                          participants=resident,
                                          start__date__gte=timezone.localtime().date()
                                          ).order_by('start')
    return result


def cancel_event(planning_event_id, resident):
    pl_event = PlanningEvent.objects.get(id=planning_event_id)
    log_calendar.info(f"cancelling event  with id :{planning_event_id}, google id = {pl_event.gg_event_id}")
    update_google_calendar(pl_event, resident, delete=True)
    if pl_event.event.is_activity:
        pl_event.participants.remove(resident)
    else:
        pl_event.delete()


# here is the interaction with the google calendar
def update_google_calendar(instance: PlanningEvent, resident: ProfileSerenicia, delete=False):
    user = instance.event.organizer.user
    start = instance.start
    end = instance.end
    task = instance.event.type
    comment = instance.event_comment
    event = {
        "summary": task + "/" + user.first_name + ' ' + user.last_name,
        "description": comment,
        "creator": {
            "id": resident.user.first_name + " " + resident.user.last_name,
        },
        "organizer": {
            "id": user.first_name + " " + user.last_name,
        },
        "start": {
            "dateTime": start.isoformat(),  # start dt
            "timeZone": "UTC"
        },
        "end": {
            "dateTime": end.isoformat(),  # end dt, may need to adapt start + delta duration depending on event kind
            "timeZone": "UTC"
        },
        "transparency": "opaque",  # blocks slot
    }
    try:
        scopes = ['https://www.googleapis.com/auth/calendar']
        key = resident.service_account_file
        credentials = gc_api.service_account.Credentials.from_service_account_info(key, scopes=scopes)
        access = gc_api.build('calendar', 'v3', credentials=credentials)
        if delete:
            gc_api.delete_event(access, resident.cal_id, instance.gg_event_id)
            return True
        else:
            gg_event = gc_api.add_event(access, resident.cal_id, event)
            return gg_event
    except Exception as e:
        log_calendar.error(f"could not update gg calendar -> {e}")
        pass
