import os
import sys

import csv
from django.contrib.auth.models import Group
from django.db import IntegrityError
from smtplib import SMTPRecipientsRefused, SMTPAuthenticationError
from app1_base.models import Client, User, Profile
from app4_ehpad_base.models import  ProfileSerenicia
from datetime import datetime
import re

# ------------------------------------------------------------------------------
# Because this script have to be run in a separate process from manage.py
# you need to set up a Django environnement to use the Class defined in
# the Django models. It is necesssary to interact with the Django database
# ------------------------------------------------------------------------------
# to get the projet.settings it is necessary to add the parent directory
# to the python path
try:
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
except NameError:
    sys.path.append(os.path.abspath('..'))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "projet.settings.settings")
import django

django.setup()


def format_date(date):
    ret = datetime.strptime(date, '%d/%m/%Y').date().isoformat()
    return ret


def format_tel_number(number):
    tel = re.sub('[^0-9]+', '', number)  # replace all non-digit char by ''
    return tel


def format_username(last_name, first_name):
    username = last_name.lower().strip() + "." + first_name.lower().strip()  # lower all char and delete unnecessary whitespace
    username = re.sub('\s+', ' ', username)  # replace multiple whitespace by one
    username = re.sub('\s+', '-', username)  # replace whitespace by '-'
    username = re.sub('-+', '-', username)  # replace multiple '-' by one
    return username


def updateclients():
    file_path = "/Residents.csv"
    file = open(file_path, "r", encoding='latin1')
    try:
        reader = csv.DictReader(file)
        for row in reader:
            birth_date = format_date(row['Date \nNaissance'])
            entry_date = format_date(row['Entrée\nEHPAD'])
            first_name = row['Résident'].split(' ')[1]
            last_name = row['Résident'].split(' ')[0]
            created_client, is_created = Client.objects.update_or_create(first_name=first_name,
                                                                         name=last_name)
            print("\n", created_client.id, " ", created_client.name, "", created_client.first_name, "is created : ",
                  is_created)
            ClientsSerenicia.objects.update_or_create(client=created_client,
                                                      titan_key=row['Résident'],
                                                      birth_date=birth_date,
                                                      entry_date=entry_date)
            if 'Hospitalisé' in row['Type de mouvement']:
                ClientsSerenicia.objects.filter(client=created_client).update(status='2')
            username = format_username(first_name, last_name + '.' + str(created_client.video_call_key))
            created_user, is_created = User.objects.update_or_create(first_name=first_name,
                                                                     last_name=last_name,
                                                                     username=username,
                                                                     )
            family_group = Group.objects.get(name='résident')
            family_group.user_set.add(created_user)
            created_profile, profile_is_created = Profile.objects.update_or_create(user=created_user,
                                                                                   client=created_client)
            ProfileSerenicia.objects.update_or_create(profile=created_profile)
    finally:
        file.close()
    return None


def updatefamilyusers():
    file_path = "/Lien_residents_familles.csv"
    file = open(file_path, "r", encoding='latin1')
    try:
        reader = csv.DictReader(file)
        for row in reader:
            is_created = False
            mobile = format_tel_number(row['Portable'])
            tel = format_tel_number(row['Téléphone'])
            username = format_username(row['Nom'], row['Prénom'])
            affected_client = Client.objects.get(clientsserenicia__titan_key=row['Résident'])
            try:
                created_obj, is_created = User.objects.update_or_create(last_name=row['Nom'],
                                                                        first_name=row['Prénom'],
                                                                        email=row['Mail'],
                                                                        username=username,
                                                                        )
            except IntegrityError as err:
                print(err)
                known_user = User.objects.get(username=username)
                if known_user.profile.client == affected_client or known_user.email == row[
                    'Mail']:  # user and client already registered
                    created_obj = known_user
                else:
                    print("\nTRYING TO CHANGE USERNAME\n")  # a user with this first name and last name already exist
                    username = username + "." + affected_client.name.lower()
                    created_obj, is_created = User.objects.update_or_create(last_name=row['Nom'],
                                                                            first_name=row['Prénom'],
                                                                            email=row['Mail'],
                                                                            username=username)
                    # profile_obj, profile_is_created = Profile.objects.update_or_create(user=created_obj)
                    # ProfileSerenicia.objects.update_or_create(profile=profile_obj)
            family_group = Group.objects.get(name='famille')
            family_group.user_set.add(created_obj)
            print("\n", created_obj.id, " ", created_obj.last_name, "", created_obj.first_name, "is created : ",
                  is_created, " username : ", username)
            try:
                profile_obj, is_created = Profile.objects.update_or_create(user=created_obj,
                                                                           client=affected_client,
                                                                           phone_number=mobile,
                                                                           phone_number_0=tel,
                                                                           phone_number_1=row['Fax'],
                                                                           created_by='import script')
                profile_obj, is_created = ProfileSerenicia.objects.get_or_create(profile=profile_obj)
            except IntegrityError as err:
                print(err)
                print("\nADD CLIENT IN LIST\n")  # multiple affected client
                # created_obj, is_created = User.objects.get(last_name=row['Nom'],
                #                                            first_name=row['Prénom'],
                #                                            email=row['Mail'])
                print("GET USER")
                profile_obj, profile_is_created = Profile.objects.get_or_create(user=created_obj)
                print("GET PROFILE")
                profile_obj, profile_is_created = ProfileSerenicia.objects.get_or_create(profile=profile_obj)
                print('GET PROFILESERENICIA')
                profile_obj.client_list.add(affected_client)
                affected_client = Client.objects.get(pk=profile_obj.profile.client.id)
                profile_obj.client_list.add(affected_client)
                profile_obj.save()
            except SMTPRecipientsRefused as err:
                print(err)
                print("\nDELETING BAD MAIL IN USER")  # bad email registered, deleting it to pass the email validator
                User.objects.filter(username=username).update(email='')
                created_obj = User.objects.get(username=username)
                Profile.objects.update_or_create(user=created_obj,
                                                 client=affected_client,
                                                 phone_number=mobile,
                                                 phone_number_0=tel,
                                                 phone_number_1=row['Fax'],
                                                 created_by='import script')
    finally:
        file.close()
    return None


def updatecaregiverusers():
    file_path = "/Lien_residents_intervenants_separator_;.csv"
    file = open(file_path, "r", encoding='latin1')
    try:
        reader = csv.DictReader(file, delimiter=";")
        for row in reader:
            tel1 = format_tel_number(row['Tel1'])
            tel2 = format_tel_number(row['Tel2'])
            mobile = format_tel_number(row['Tel Portable'])
            fax = format_tel_number(row['Fax'])
            username = format_username(row['Nom'], row['Prénom'])
            try:
                created_obj, is_created = User.objects.update_or_create(last_name=row['Nom'],
                                                                        frst_name=row['Prénom'],
                                                                        email=row['Mail'],
                                                                        username=username,
                                                                        )
            except IntegrityError as err:
                print(err)
                created_obj = User.objects.get(username=username)
                is_created = False
            print("\n", created_obj.id, " ", created_obj.last_name, " ", created_obj.first_name, "is created : ",
                  is_created, " username : ", username)
            family_group = Group.objects.get(name='caregiver')
            family_group.user_set.add(created_obj)
            try:
                profile_obj, profile_is_created = Profile.objects.update_or_create(user=created_obj,
                                                                                   phone_number=tel1,
                                                                                   phone_number_0=tel2,
                                                                                   phone_number_1=mobile,
                                                                                   phone_number_2=fax,
                                                                                   created_by='import script'
                                                                                   )
            except IntegrityError as err:
                print(err)
                profile_obj = Profile.objects.get(user=created_obj)
            except SMTPRecipientsRefused as err:
                print(err)
                print("\nDELETING BAD MAIL IN USER")  # bad email registered, deleting it to pass the email validator
                User.objects.filter(username=username).update(email='')
                created_obj = User.objects.get(username=username)
                profile_obj, profile_is_created = Profile.objects.update_or_create(user=created_obj,
                                                                                   phone_number=tel1,
                                                                                   phone_number_0=tel2,
                                                                                   phone_number_1=mobile,
                                                                                   phone_number_2=fax,
                                                                                   created_by='import script'
                                                                                   )
            profile_obj, is_created = ProfileSerenicia.objects.update_or_create(profile=profile_obj)
            if row['Résidant']:
                print("\nADDING CLIENT")
                affected_client = Client.objects.get(clientsserenicia__titan_key=row['Résidant'])
                profile_obj.client_list.add(affected_client)
                profile_obj.save()
    finally:
        file.close()
    return None


def updatefamilypassword():
    print("SETTING PASSWORD FOR FAMILY USERS")
    listUser = User.objects.filter(groups__permissions__codename='view_family')
    for familyuser in listUser:
        print("\nSET PASSWORD FOR : ", familyuser.username)
        familyuser.set_password("serenicia")
        familyuser.save()
    print("done.")
