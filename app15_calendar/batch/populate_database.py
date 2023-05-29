import os
import sys

# Because this script have to be run in a separate process from manage.py
# you need to set up a Django environnement to use the Class defined in
# the Django models. It is necesssary to interact witht the Django database
# ------------------------------------------------------------------------------
# to get the projet.settings it is necessary to add the parent directory
# to the python path

try:
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
except NameError:
    sys.path.append(os.path.abspath('../..'))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "projet.settings.settings")
import django

django.setup()

from app4_ehpad_base.models import PlanningEvent as PlEvApp3
from app4_ehpad_base.models import Event as EventApp3
from app4_ehpad_base.models import Location as LocationApp3
from app4_ehpad_base.models import Recurrence as RecurrenceApp3

from app15_calendar.models import PlanningEvent, Event, Location, Recurrence


def copy_location():
    objects = LocationApp3.objects.all()
    print(f'COPYING {objects.count()} LOCATION FROM APP3 TO app15_calendar...')
    for loc in objects:
        new_loc = Location.objects.create(name=loc.name, photo=loc.photo)
        loc.new_pk = new_loc.id
        loc.save()
    print(f'LOCATION DONE : {Location.objects.count()} CREATED')


def copy_event():
    objects = EventApp3.objects.all()
    print(f'COPYING {objects.count()} EVENT FROM APP3 TO app15_calendar...')
    for event in objects:
        new_event = Event.objects.create(type=event.type, organizer=event.organizer, public=event.public,
                                         is_activity=event.is_activity, is_visit=event.is_visit,
                                         is_birthday=event.is_birthday, objective=event.objective,
                                         protected_unit_only=event.protected_unit_only)
        event.new_pk = new_event.id
        event.save()
        try:
            location = Location.objects.get(id=event.location.new_pk)
            new_event.location = location
            new_event.save()
        except AttributeError:
            pass
    print(f'EVENT DONE : {Event.objects.count()} CREATED')


def copy_recurrence():
    objects = RecurrenceApp3.objects.all()
    print(f'COPYING {objects.count()} RECURRENCE FROM APP3 TO app15_calendar...')
    for rec in objects:
        event = Event.objects.get(id=rec.event.new_pk)
        Recurrence.objects.create(event=event, start=rec.start, end=rec.end, start_time=rec.start_time,
                                  end_time=rec.end_time, day=rec.day)
    print(f'RECURRENCE DONE : {Recurrence.objects.count()} CREATED')


def copy_planningevent():
    objects = PlEvApp3.objects.all()
    print(f'COPYING {objects.count()} PLANNINGEVENT FROM APP3 TO app15_calendar...')
    for pl_ev in objects:
        new_pl_ev = PlanningEvent.objects.create(start=pl_ev.start, end=pl_ev.end, event_comment=pl_ev.event_comment,
                                                 gg_event_id=pl_ev.gg_event_id, thumbnail_url=pl_ev.thumbnail_url,
                                                 blog_post=pl_ev.blog_post)
        pl_ev.new_pk = new_pl_ev.id
        pl_ev.save()
        try:
            event = Event.objects.get(id=pl_ev.event.new_pk)
            new_pl_ev.event = event
            new_pl_ev.save()
        except AttributeError:
            pass
        new_pl_ev.participants.set(pl_ev.participants.all())
        new_pl_ev.attendance.set(pl_ev.attendance.all())
    print(f'PLANNINGEVENT DONE : {PlanningEvent.objects.count()} CREATED')


print('------- START POPULATE app15_calendar DATABASE -------')
copy_location()
copy_event()
copy_recurrence()
copy_planningevent()
print('------- POPULATE DATABASE DONE -------')


