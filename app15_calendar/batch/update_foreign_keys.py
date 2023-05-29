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

from app6_care.models import CarePlanEvent
from app4_ehpad_base.models import MealBooking, Photos
from app10_social_activities.models import Evaluation

from app15_calendar.models import PlanningEvent, PlanningEventBooking, PlanningEventPhotos


def update_careplanevent():
    print(f'UPDATING CARE PLAN EVENT...')
    for cp_ev in CarePlanEvent.objects.filter(planning_event__isnull=False):
        CarePlanEvent.objects.filter(id=cp_ev.id).update(
            planning_event_new=PlanningEvent.objects.get(id=cp_ev.planning_event.new_pk))
    print(f'{CarePlanEvent.objects.filter(planning_event__isnull=False).count()} CARE PLAN EVENT UPDATED')


def update_evaluation():
    print('UPDATING EVALUATION...')
    for ev in Evaluation.objects.all():
        Evaluation.objects.filter(id=ev.id).update(activity_new=PlanningEvent.objects.get(id=ev.activity.new_pk))
    print(f'{Evaluation.objects.count()} EVALUATION UPDATED')


def update_mealbooking():
    print(f'UPDATING MEAL BOOKING...')
    result = 0
    for mb in MealBooking.objects.filter(planning_event__isnull=False):
        try:
            PlanningEventBooking.objects.create(booking=mb,
                                                planning_event=PlanningEvent.objects.get(pk=mb.planning_event.new_pk))
            result += 1
        except Exception as error:
            print(error)
    print(f'{result} MEAL BOOKING CREATED/UPDATED')


def update_photos():
    print('UPDATING PHOTOS...')
    result = 0
    for photo in Photos.objects.filter(activity__isnull=False):
        try:
            PlanningEventPhotos.objects.create(photos=photo,
                                               planning_event=PlanningEvent.objects.get(pk=photo.planning_event.new_pk))
            result += 1
        except Exception as error:
            print(error)
    print(f'{result} PHOTOS CREATED/UPDATED')


print('------- START UPDATE FOREIGN KEYS -------')
print('APP3')
update_mealbooking()
update_photos()
print('APP3 DONE')
print('--------------')
print('APP6')
update_careplanevent()
update_evaluation()
print('APP6 DONE')
print('------- UPDATE FK DONE -------')
