import os
import sys

# Because this script have to be run in a separate process from manage.py
# you need to set up a Django environnement to use the Class defined in
# the Django models. It is necesssary to interact witht the Django database
# ------------------------------------------------------------------------------
# to get the projet.settings it is necessary to add the parent directory
# to the python path

try:
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
except NameError:
    sys.path.append(os.path.abspath('../..'))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "projet.settings.settings")
import django

django.setup()

from app1_base.models import Client, Profile
from app4_ehpad_base.models import ProfileSerenicia
from django.contrib.auth.models import User, Group
import re


def format_username(last_name, first_name):
    username = last_name.lower().strip() + "." + first_name.lower().strip()  # lower all char and delete unnecessary whitespace
    username = re.sub('\s+', ' ', username)  # replace multiple whitespace by one
    username = re.sub('\s+', '-', username)  # replace whitespace by '-'
    username = re.sub('-+', '-', username)  # replace multiple '-' by one
    return username


def actualize_user_resident():
    listclient = Client.objects.all()
    for client in listclient:
        print('\n---------------------\n')
        print('Client : ', client)
        username = format_username(client.first_name, client.name + '.' + str(client.video_call_key))
        user, user_is_created = User.objects.get_or_create(first_name=client.first_name, last_name=client.name, username=username)
        if user_is_created:
            print('User créé, username : ', user.username)
        else:
            print('User existant : ', user.username)
        family_group = Group.objects.get(name='resident')
        family_group.user_set.add(user)
        profile, profile_is_created = Profile.objects.get_or_create(user=user, client=client)
        if profile_is_created:
            print('Profile créé')
        else:
            print('Profile déjà existant.')
        profileserenicia, profseren_is_created = ProfileSerenicia.objects.get_or_create(user=user)
        try:
            clientsserenicia = ClientsSerenicia.objects.get(client=client)
            profileserenicia.folder = client.folder
            profileserenicia.external_key = clientsserenicia.external_key
            profileserenicia.birth_city = clientsserenicia.birth_city
            profileserenicia.birth_date = clientsserenicia.birth_date
            profileserenicia.entry_date = clientsserenicia.entry_date
            profileserenicia.service_account_file = clientsserenicia.service_account_file
            profileserenicia.cal_id = clientsserenicia.cal_id
            profileserenicia.titan_key = clientsserenicia.titan_key
            profileserenicia.pics_total = clientsserenicia.pics_total
            profileserenicia.pics_last = clientsserenicia.pics_last
            profileserenicia.routines_protocol = clientsserenicia.routines_protocol
            profileserenicia.save()
            print('ProfileSerenicia actualisé')
        except Exception as err:
            print(err)


def create_new_user(username):
    print('\n---------------------\n')
    user, user_is_created = User.objects.get_or_create(username=username)
    if user_is_created:
        Profile.objects.create(user=user)
        ProfileSerenicia.objects.create(user=user)
        print('user créé : ', user)
    else:
        print('ce nom de user existe déjà : ', user.username)

