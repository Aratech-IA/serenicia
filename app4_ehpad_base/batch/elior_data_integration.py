import os
import sys

# Because this script have to be run in a separate process from manage.py
# you need to set up a Django environnement to use the Class defined in
# the Django models. It is necesssary to interact witht the Django database
# ------------------------------------------------------------------------------
# to get the projet.settings it is necessary to add the parent directory
# to the python path
from datetime import datetime

try:
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
except NameError:
    sys.path.append(os.path.abspath('../..'))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "projet.settings.settings")

import django
django.setup()


from app4_ehpad_base.models import Entree, MainDish, Accompaniment, Dessert, Meal
import csv


file_path = "/App/data_elior/MenuHelios.csv"
meal_type = {'HD': Entree, 'PP': MainDish, 'LG': Accompaniment, 'DE': Dessert}
try:
    with open(file_path, 'r', encoding='utf-16') as file:
        for row in csv.DictReader(file, delimiter=';'):
            try:
                meal, created = meal_type[row['GROUPEPLAT']].objects.get_or_create(name=row['LIBELLEPLAT'])
                date = datetime.strptime(row['DATEMENU'], '%Y%m%d').date()
                menu, created = Meal.objects.get_or_create(date=date, substitution=False)
                menu_sub, created = Meal.objects.get_or_create(date=date, substitution=True)
                if isinstance(meal, Entree):
                    if menu.entree:
                        menu = menu_sub
                    menu.entree = meal
                elif isinstance(meal, MainDish):
                    if menu.main_dish:
                        menu = menu_sub
                    menu.main_dish = meal
                elif isinstance(meal, Accompaniment):
                    if menu.accompaniment:
                        menu = menu_sub
                    menu.accompaniment = meal
                elif isinstance(meal, Dessert):
                    if menu.dessert:
                        menu = menu_sub
                    menu.dessert = meal
                menu.save()
            except KeyError:
                pass
except Exception as err:
    print(f'error : {err}')
