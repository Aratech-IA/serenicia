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

from app4_ehpad_base.models import Meal, MealPresentation, PresentationType
import logging
from app1_base.log import Logger


log = Logger('populate_mealpresentation', level=logging.ERROR).run()


for menu in Meal.objects.all():
    log.debug(f'{menu.date} - {menu.type} - {menu.entree} - {menu.main_dish}')
    normal = PresentationType.objects.get(type='normal')
    mixed = PresentationType.objects.get(type='mixé')
    if menu.photo_entree:
        log.debug('création photo entrée normale')
        MealPresentation.objects.create(item='entree', meal=menu, presentation=normal, photo=menu.photo_entree)
    if menu.photo_main_dish:
        log.debug('création photo plat principal normal')
        MealPresentation.objects.create(item='main_dish', meal=menu, presentation=normal, photo=menu.photo_main_dish)
    if menu.photo_dessert:
        log.debug('création photo dessert normal')
        MealPresentation.objects.create(item='dessert', meal=menu, presentation=normal, photo=menu.photo_dessert)
    if menu.photo_entree_mixed:
        log.debug('création photo entrée mixée')
        MealPresentation.objects.create(item='entree', meal=menu, presentation=mixed, photo=menu.photo_entree_mixed)
    if menu.photo_main_dish_mixed:
        log.debug('création photo plat principal mixé')
        MealPresentation.objects.create(item='main_dish', meal=menu, presentation=mixed, photo=menu.photo_main_dish_mixed)
    if menu.photo_dessert_mixed:
        log.debug('création photo dessert mixé')
        MealPresentation.objects.create(item='dessert', meal=menu, presentation=mixed, photo=menu.photo_dessert_mixed)
    log.debug('-------------------------------------------')
