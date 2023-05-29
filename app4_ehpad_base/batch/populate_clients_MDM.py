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

from app4_ehpad_base.models import Client
from app1_base.models import Sector
from projet.settings.settings import CLIENT_CP, CLIENT_ADRESS, CLIENT_CITY



listclient = Client.objects.all()
room_number = 101
sector = 1
for client in listclient:
    print('\n------------------------------')
    print(client)
    tmp_number = room_number - (sector*100)
    if tmp_number == 13:
        tmp_number = 14
    if tmp_number > 15:
        tmp_number = 1
        sector += 1
    room_number = (sector*100)+tmp_number
    client.sector = Sector.objects.get(number=sector)
    client.room_number = room_number
    client.name = ''
    client.first_name = ''
    client.cp = CLIENT_CP
    client.city = CLIENT_CITY
    client.adress = CLIENT_ADRESS
    print('secteur : ', client.sector, '\nN° chambre : ', client.room_number)
    client.save()
    room_number += 1
