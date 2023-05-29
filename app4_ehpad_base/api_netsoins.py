import os
import sys

# ------------------------------------------------------------------------------
# Because this script have to be run in a separate process from manage.py
# you need to set up a Django environnement to use the Class defined in
# the Django models. It is necesssary to interact with the Django database
# ------------------------------------------------------------------------------
# to get the projet.settings it is necessary to add the parent directory
# to the python path

from django.db import IntegrityError
from django.utils import timezone

try:
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
except NameError:
    sys.path.append(os.path.abspath('..'))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "projet.settings.settings")
import django

django.setup()

from random import randint
from django.contrib.auth.models import User, Group, Permission
from django.core.exceptions import ObjectDoesNotExist
from app1_base import log
from projet.settings.settings import NETSOINS_URL, NETSOINS_TYPE, NETSOINS_KEY, CLIENT_CP, CLIENT_ADRESS, CLIENT_CITY, NOM_EHPAD
import base64
import requests
import json
from app1_base.models import Client, SubSector, Profile, Sector
from app4_ehpad_base.models import ProfileSerenicia, Card
import ssl
from urllib3 import poolmanager
from urllib.parse import quote_plus
import re
from django.utils.translation import gettext_lazy as _

log_resident = log.Logger('api_netsoins_resident', level=log.logging.DEBUG, file=True).run()
log_family = log.Logger('api_netsoins_family', level=log.logging.DEBUG, file=True).run()
log_staff = log.Logger('api_netsoins_staff', level=log.logging.DEBUG, file=True).run()
log_cards = log.Logger('api_netsoins_cards', level=log.logging.DEBUG, file=True).run()


# ----------------------------------------------------------------------------------------------------------------------


class TLSAdapter(requests.adapters.HTTPAdapter):
    def init_poolmanager(self, connections, maxsize, block=False):
        """Create and initialize the urllib3 PoolManager."""
        ctx = ssl.create_default_context()
        ctx.set_ciphers('DEFAULT@SECLEVEL=1')
        self.poolmanager = poolmanager.PoolManager(
            num_pools=connections,
            maxsize=maxsize,
            block=block,
            ssl_version=ssl.PROTOCOL_TLS,
            ssl_context=ctx)


def get_netsoins_url_get(option):
    return NETSOINS_URL + option + '?' + NETSOINS_TYPE + '&' + NETSOINS_KEY + '&output=json&statut_actif=tous&statut_archive=tous'


def get_netsoins_url_post(option):
    return NETSOINS_URL + option + '?' + NETSOINS_TYPE + '&' + NETSOINS_KEY + '&output=json&input=json'


def call_netsoins_data(option):
    print(f'\n\n\n ------------- CALL_NETSOINS_DATA {option} ------------- \n\n\n')
    url = get_netsoins_url_get(option)
    session = requests.session()
    session.mount('https://', TLSAdapter())
    res = session.get(url)
    result = json.loads(res.text)
    list_data = result[option]
    print('len_data: ', len(list_data))
    for data in list_data:
        print(data)
    print('\n\n\n ------------- DONE ------------- \n\n\n')


# ----------------------------------------------------------------------------------------------------------------------
#                              ACTUALIZE URI_NETSOINS FIELD FOR EXISTANT RESIDENT
# ----------------------------------------------------------------------------------------------------------------------
def update_uri_netsoins(option):
    print('\n\n\n ------------- UPDATE URI FIELD FROM NETSOINS / START ------------- \n\n\n')
    url = get_netsoins_url_get(option)
    session = requests.session()
    session.mount('https://', TLSAdapter())
    res = session.get(url)
    result = json.loads(res.text)
    listresident = result[option]
    listerror = []
    for resident in listresident:
        try:
            tmp_user = User.objects.get(last_name=resident['Nom'], first_name=resident['Prenom'])
            tmp_user.profileserenicia.uri_netsoins = resident['Uri']
            tmp_user.profileserenicia.save()
        except Exception as err:
            listerror.append([resident, err])
    print('\nDetails:')
    if len(listerror) > 0:
        for error in listerror:
            print('\n', error[0])
            print('\n', error[1])
            print('\n-----------------------------------------------------')
    print('\nError count :', len(listerror))
    print('\n\n\n ------------- UPDATE URI FIELD FROM NETSOINS / END ------------- \n\n\n')


# ----------------------------------------------------------------------------------------------------------------------
#                   CREATE SECTOR + CLIENT WITH ADRESS, CP, CITY AND ROOM_NUMBER WITH SECTOR RELATION
# ----------------------------------------------------------------------------------------------------------------------

def manually_first_init():
    print('\n\n\n ------------- FIRST_INIT ------------- \n\n\n')
    create_netsoins_room()
    netsoins_sector_and_room()
    import_group_netsoins()
    print('\n\n\n ------------- INIT DONE ------------- \n\n\n')


def temporary_room_number_rule(room_number):
    room_number = room_number.replace(' ', '')
    if room_number[-1].lower() == 'f':
        room_number = room_number.lower().replace('f', '1')
    elif room_number[-1].lower() == 'p':
        room_number = room_number.lower().replace('p', '2')
    return room_number


def create_netsoins_room():
    print('\n\n\n ------------- CREATE NETSOINS ROOM ------------- \n\n\n')
    url = get_netsoins_url_get('EtablissementChambre')
    session = requests.session()
    session.mount('https://', TLSAdapter())
    res = session.get(url)
    result = json.loads(res.text)
    listroom = result['EtablissementChambre']
    sector, is_created = Sector.objects.get_or_create(name=NOM_EHPAD)
    base_subsector = SubSector.objects.create(number=0, name=_('Unaffected'), sector=sector)
    for room in listroom:
        tmp_room = Client.objects.create(room_number=temporary_room_number_rule(room['Libelle']), sector=base_subsector)
        print(tmp_room.room_number, ' = ', room['Libelle'])
    print('\n\n\n ------------- DONE ------------- \n\n\n')


def netsoins_sector_and_room():
    url = get_netsoins_url_get('EtablissementSousSecteur')
    session = requests.session()
    session.mount('https://', TLSAdapter())
    res = session.get(url)
    result = json.loads(res.text)
    listsubsector = result['EtablissementSousSecteur']
    sector, is_created = Sector.objects.get_or_create(name=NOM_EHPAD)
    for subsector in listsubsector:
        tmp_subsector, is_created = SubSector.objects.get_or_create(number=subsector['Libelle'].lower().replace('secteur ', ''), sector=sector)
        tmp_subsector.name = subsector['Libelle'][:]
        tmp_subsector.save()
        for room in subsector['EtablissementChambres']:
            if len(room['Libelle']) > 2:
                tmp_client, is_created = Client.objects.get_or_create(room_number=temporary_room_number_rule(room['Libelle']))
                print(f"update client.room_number : {temporary_room_number_rule(room['Libelle'])}")
                tmp_client.sector = tmp_subsector
                tmp_client.cp = CLIENT_CP
                tmp_client.adress = CLIENT_ADRESS
                tmp_client.city = CLIENT_CITY
                tmp_client.save()
    print("actualize client and sector, done.")


# ----------------------------------------------------------------------------------------------------------------------
#                               GENERATE USERNAME IN FORMAT : first-name.last-name
# ----------------------------------------------------------------------------------------------------------------------
def create_username(last_name, first_name=None, resident=False):
    # lower all char and delete unnecessary whitespace
    if first_name and first_name != '':
        username = first_name.lower().strip() + "." + last_name.lower().strip()
    else:
        username = last_name.lower().strip()
    # replace multiple whitespace by one
    username = re.sub('\s+', ' ', username)
    # replace whitespace by '-'
    username = re.sub('\s+', '-', username)
    # replace multiple '-' by one
    username = re.sub('-+', '-', username)
    if resident:
        username += '.' + str(randint(1000, 9999))
    return username

def actualize_password_by_group(group_name):  # DEPRECATED
    list_user = User.objects.filter(groups__name=group_name)
    for user in list_user:
        user.set_password(user.username)
        user.save()


def check_existing_user(first_name, last_name, uri=None, logger=None, birth_date=None, email=None, resident=False,
                        created_by='netsoins_import'):
    if not first_name or not last_name:
        if logger:
            logger.debug(f"erreur création user, donnée(s) manquante(s) : nom={last_name}, prénom={first_name}")
        return None
    if birth_date:
        birth_date = birth_date.split('T')[0]
    try:
        user = User.objects.prefetch_related('profileserenicia', 'profile').get(last_name__iexact=last_name,
                                                                                first_name__iexact=first_name,
                                                                                profileserenicia__birth_date=birth_date)
        if logger:
            logger.debug(f"user existant : {user} (id: {user.id})")
        result = user.profileserenicia
    except ObjectDoesNotExist:
        if logger:
            logger.debug(f'user sans date de naissance')
        try:
            user = User.objects.prefetch_related('profileserenicia', 'profile').get(last_name__iexact=last_name,
                                                                                    first_name__iexact=first_name,
                                                                                    email__iexact=email)
            if logger:
                logger.debug(f"user existant : {user} (id: {user.id})")
            result = user.profileserenicia
        except ObjectDoesNotExist:
            if logger:
                logger.debug(f"creation : {last_name}, {first_name}, {birth_date}, {email}")
            if resident:
                username = create_username(last_name=last_name, first_name=first_name, resident=True)
            else:
                username = create_username(last_name=last_name, first_name=first_name)
            users_nb = User.objects.filter(username=username).count()
            if users_nb > 0:
                username += str(users_nb + 1)
            tmp_user = User.objects.create(username=username)
            tmp_user.set_password(tmp_user.username)
            Profile.objects.create(user=tmp_user, created_by=created_by)
            result = ProfileSerenicia.objects.create(user=tmp_user)
    if uri:
        result.uri_netsoins = uri
    if birth_date:
        result.birth_date = birth_date
    result.save()
    if email:
        result.user.email = email
        result.user.save()
    return result


# ----------------------------------------------------------------------------------------------------------------------
#                               UPDATE OR CREATE RESIDENT FOM NETSOINS DATABASE
#                               USE URI_NETSOINS AS UNIQUE KEY TO IDENTIFY USER
#                                   ADD ROOM_NUMBER, DELETE-IT IF DECEASED
# ----------------------------------------------------------------------------------------------------------------------
def cron_netsoins_resident():
    url = get_netsoins_url_get('Resident')
    url += '&fields=Nom,Prenom,Actif,DateEntree,EtablissementChambre,Libelle,DateNaissance,ResidentBacterie,ResidentPraticien,UriPersonnel,ResidentContact,Civilite,VilleNaissance'
    session = requests.session()
    session.mount('https://', TLSAdapter())
    res = session.get(url)
    result = json.loads(res.text)
    try:
        listresident = result['Resident']
    except KeyError:
        log_resident.debug(f"liste résident vide")
    group = Group.objects.get(permissions__codename='view_residentehpad')
    for resident in listresident:
        tmp_profseren = None
        is_active = int(resident['Actif'])
        try:
            tmp_profseren = ProfileSerenicia.objects.prefetch_related('user',
                                                                     'user__profile').get(uri_netsoins=resident['Uri'])
        except ObjectDoesNotExist:
            if is_active:
                tmp_profseren = check_existing_user(first_name=resident.get('Prenom'), last_name=resident.get('Nom'),
                                                   birth_date=resident.get('DateNaissance'), uri=resident.get('Uri'),
                                                   resident=True, logger=log_resident)
        if tmp_profseren:
            try:
                if is_active:
                    room = Client.objects.get(room_number=temporary_room_number_rule(resident['EtablissementChambre']['Libelle']))
                    tmp_profseren.user.profile.client = room
                else:
                    log_resident.debug(f"inactif : {resident['Nom']}, prenom: {resident['Prenom']}")
                    tmp_profseren.status = 'deceased'
                    tmp_profseren.user.profile.client = None
                    tmp_profseren.user.is_active = False
                    if not tmp_profseren.date_status_deceased:
                        tmp_profseren.date_status_deceased = timezone.localdate()
                group.user_set.add(tmp_profseren.user)
                if 'DateEntree' in resident:
                    tmp_profseren.entry_date = resident.get('DateEntree').split('T')[0]
                tmp_profseren.user.last_name = resident.get('Nom')
                tmp_profseren.user.first_name = resident.get('Prenom')
                if 'ResidentBacteries' in resident:
                    tmp_profseren.bacterium = True
                if 'DateNaissance' in resident:
                    tmp_profseren.birth_date = resident.get('DateNaissance').split('T')[0]
                tmp_profseren.birth_city = resident.get('VilleNaissance')
                if resident.get('Civilite') == 'MONSIEUR':
                    tmp_profseren.user.profile.civility = 'Mr'
                elif resident.get('Civilite') == 'MADAME' or resident.get('Civilite') == 'MADEMOISELLE':
                    tmp_profseren.user.profile.civility = 'Mrs'
                tmp_profseren.user.profile.save()
                tmp_profseren.user.save()
                tmp_profseren.save()
                if resident.get('ResidentPraticiens'):
                    scope = ['view_ide', 'view_ash', 'view_as']
                    for caregiver in resident.get('ResidentPraticiens'):
                        try:
                            if not ProfileSerenicia.objects.get(uri_netsoins=caregiver.get('UriPersonnel'),
                                                                user__groups__permissions__codename__in=scope):
                                ProfileSerenicia.objects.get(uri_netsoins=caregiver.get('UriPersonnel'),
                                                             ).user_list.add(tmp_profseren.user.profile)
                        except ObjectDoesNotExist:
                            log_resident.debug(f"Soignant inconnu : {caregiver.get('UriPersonnel')}")
                if resident.get('ResidentContacts'):
                    for contact in resident.get('ResidentContacts'):
                        try:
                            ProfileSerenicia.objects.get(uri_netsoins=contact.get('Uri')).user_list.add(
                                tmp_profseren.user.profile)
                        except ObjectDoesNotExist:
                            log_resident.debug(f"Contact inconnu : {contact.get('Uri')}")
            except (ValueError, KeyError):
                log_resident.debug(f"données manquantes : {tmp_profseren}")
        else:
            pass
    log_resident.debug("update resident, done.")


def cleaning_double():
    list_user = User.objects.all().exclude(groups__permissions__codename='view_residentehpad')
    for user in list_user:
        if user.username[-1] == "2":
            user.delete()


# ----------------------------------------------------------------------------------------------------------------------
#                                    UPDATE OR CREATE STAFF FOM NETSOINS DATABASE
#                                   USE URI_NETSOINS AS UNIQUE KEY TO IDENTIFY USER
#                              ADD NUMBER TO USERNAME IF first-name.last_name ALREADY EXIST
#                                 !! THIS FONCTION DON'T ADD USER'S PERMISSIONS !!
# ----------------------------------------------------------------------------------------------------------------------
def cron_netsoins_staff():
    url = get_netsoins_url_get('Personnel')
    session = requests.session()
    session.mount('https://', TLSAdapter())
    res = session.get(url)
    result = json.loads(res.text)
    liststaff = result['Personnel']
    for staff in liststaff:
        tmp_profseren = None
        is_active = int(staff['Actif'])
        try:
            tmp_profseren = ProfileSerenicia.objects.get(uri_netsoins=staff['Uri'])
        except ObjectDoesNotExist:
            if is_active:
                tmp_profseren = check_existing_user(first_name=staff.get('Prenom'), last_name=staff.get('Nom'),
                                                   birth_date=staff.get('DateNaissance'), uri=staff.get('Uri'),
                                                   logger=log_staff)
        if tmp_profseren:
            if not is_active:
                tmp_profseren.user.is_active = False
            if 'Prenom' in staff:
                tmp_profseren.user.first_name = staff.get('Prenom')
            tmp_profseren.user.last_name = staff.get('Nom')
            if 'DateNaissance' in staff:
                tmp_profseren.birth_date = staff.get('DateNaissance').split('T')[0]
            if staff.get('Civilite') == 'MONSIEUR':
                tmp_profseren.user.profile.civility = 'M.'
            elif staff.get('Civilite') == 'MADAME' or staff.get('Civilite') == 'MADEMOISELLE':
                tmp_profseren.user.profile.civility = 'Mme'
            tmp_profseren.user.profile.adress = staff.get('Adresse')
            tmp_profseren.user.profile.cp = staff.get('CodePostal')
            tmp_profseren.user.profile.city = staff.get('Ville')
            tmp_profseren.user.profile.save()
            tmp_profseren.user.save()
            tmp_profseren.save()
    log_staff.debug("update staff, done.")


def init_group_from_netsoins():
    group_perms = [{'name': 'Ambulance - Taxi - VSL', 'perm': []},
                   {'name': 'Psychomotricien/ne', 'perm': ['view_evalmenu', 'view_user']},
                   {'name': 'Psychologue', 'perm': ['view_evalmenu', 'view_createaccount',
                                                    'view_supportproject', 'view_user']},
                   {'name': 'Pédicure - podologue', 'perm': ['view_evalmenu', 'view_user']},
                   {'name': 'Orthophoniste', 'perm': ['view_evalmenu', 'view_user']},
                   {'name': 'Kinésithérapeute', 'perm': ['view_evalmenu', 'view_user']},
                   {'name': 'Ergothérapeute', 'perm': ['view_evalmenu', 'view_user']},
                   {'name': 'Médecin - Généraliste', 'perm': ['view_evalmenu']},
                   {'name': 'Médecin - Dentiste', 'perm': ['view_evalmenu']},
                   {'name': 'Infirmier/ère', 'perm': ['view_ide', 'view_evalmenu', 'view_user', 'view_care']},
                   {'name': 'IDEC', 'perm': ['view_ide', 'view_manager', 'view_evalmenu', 'view_user',
                                             'view_care', 'view_createaccount']},
                   {'name': 'Responsable d\'hébergement', 'perm': ['view_manager', 'view_evalmenu', 'view_user',
                                                                   'view_createaccount']},
                   {'name': 'Coiffeur/feuse', 'perm': ['view_evalmenu', 'view_user']},
                   {'name': 'Responsable cuisine', 'perm': ['view_cuisine', 'view_cuisineprice',
                                                            'view_evalmenu', 'view_user']},
                   {'name': 'Cuisinier/ère', 'perm': ['view_evalmenu', 'view_cuisine']},
                   {'name': 'ASH', 'perm': ['view_ash', 'view_evalmenu', 'view_user', 'view_care']},
                   {'name': 'AMP', 'perm': ['view_as', 'view_evalmenu', 'view_user', 'view_care']},
                   {'name': 'AES', 'perm': ['view_as', 'view_evalmenu', 'view_user', 'view_care']},
                   {'name': 'AS', 'perm': ['view_as', 'view_evalmenu', 'view_user', 'view_care']},
                   {'name': 'Informaticien/ne', 'perm': ['view_user']},
                   {'name': 'Agent de service technique', 'perm': []},
                   {'name': 'Direction', 'perm': ['view_evalmenu', 'view_manager', 'view_documents', 'view_cuisine',
                                                  'view_user', 'view_client', 'view_security', 'view_communication',
                                                  'view_cuisineprice', 'view_groupreservation', 'view_createaccount',
                                                  'view_supportproject']},
                   {'name': 'Administratif',
                    'perm': ['view_evalmenu', 'view_documents', 'view_user', 'view_client']}]
    for grp in group_perms:
        try:
            new_grp = Group.objects.create(name=grp['name'])
            print(f'group created : {new_grp}')
            for codename in grp['perm']:
                new_grp.permissions.add(Permission.objects.get(codename=codename))
        except IntegrityError:
            print(f'group {grp["name"]} already exist')
    print("init group, done.")

def import_group_netsoins():
    url = get_netsoins_url_get('CategorieProfessionnelle')
    session = requests.session()
    session.mount('https://', TLSAdapter())
    res = session.get(url)
    result = json.loads(res.text)
    listgroup = result['CategorieProfessionnelle']
    for grp in listgroup:
        Group.objects.get_or_create(name=grp['Libelle'])
    print("import group, done.")

def update_staff_permissions():
    url = get_netsoins_url_get('Personnel')
    session = requests.session()
    session.mount('https://', TLSAdapter())
    res = session.get(url)
    result = json.loads(res.text)
    liststaff = result['Personnel']
    for staff in liststaff:
        if staff.get('CategorieProfessionnelle') and int(staff['Actif']):
            try:
                tmp_profseren = ProfileSerenicia.objects.get(uri_netsoins=staff['Uri'])
                grp_name = staff['CategorieProfessionnelle']['Libelle']
                grp = Group.objects.get(name=grp_name)
                grp.user_set.add(tmp_profseren.user)
            except ObjectDoesNotExist:
                log_staff.debug(
                    f'Group from update staff doesn\'t exist : {staff["CategorieProfessionnelle"]["Libelle"]}')
    log_staff.debug("update staff permissions, done.")


def cron_netsoins_family():
    url = get_netsoins_url_get('ResidentContact')
    session = requests.session()
    session.mount('https://', TLSAdapter())
    res = session.get(url)
    result = json.loads(res.text)
    listcontact = result['ResidentContact']
    listerror = []
    group = Group.objects.get(permissions__codename='view_family')
    for contact in listcontact:
        tmp_user = None
        is_active = int(contact['Actif'])
        dictvalues = {'TelephoneMobile': '', 'TelephoneFixe': '', 'Mail': '', 'Prenom': '', 'Nom': ''}
        listkeys = contact.keys()
        [dictvalues.update({key: contact.get(key)}) for key in listkeys]
        try:
            tmp_user = User.objects.get(profileserenicia__uri_netsoins=dictvalues.get('Uri'))
        except ObjectDoesNotExist:
            if is_active:
                tmp_profseren = check_existing_user(first_name=dictvalues.get('Prenom'), last_name=dictvalues.get('Nom'),
                                                   uri=dictvalues.get('Uri'), logger=log_family,
                                                   email=dictvalues.get('Mail'))
                if tmp_profseren is not None:
                    tmp_user = tmp_profseren.user
        if tmp_user:
            if is_active:
                tmp_user.profile.cp = dictvalues.get('CodePostal')
                tmp_user.profile.city = dictvalues.get('Ville')
                tmp_user.profile.adress = dictvalues.get('Adresse')
                if dictvalues.get('Civilite') == 'MONSIEUR':
                    tmp_user.profile.civility = 'M.'
                elif dictvalues.get('Civilite') == 'MADAME' or dictvalues.get('Civilite') == 'MADEMOISELLE':
                    tmp_user.profile.civility = 'Mme'
                tmp_user.profile.phone_number = dictvalues.get('TelephoneMobile').replace('.', '')
                tmp_user.profile.phone_number_0 = dictvalues.get('TelephoneFixe').replace('.', '')
                tmp_user.email = dictvalues.get('Mail')
                tmp_user.last_name = dictvalues.get('Nom')
                tmp_user.first_name = dictvalues.get('Prenom')
                group.user_set.add(tmp_user)
                tmp_user.profileserenicia.save()
                tmp_user.profile.save()
                tmp_user.save()
    for error in listerror:
        log_family.debug(error)


# ----------------------------------------------------------------------------------------------------------------------


def encode_to_base64(path):
    with open(path, 'rb') as file:
        return base64.b64encode(file.read()).decode()


def get_administrative_id(uri_netsoins):
    url = get_netsoins_url_get('Resident')
    url += "&Uri=" + quote_plus(uri_netsoins) + '&fields=IdentifiantAdministratif'
    session = requests.session()
    session.mount('https://', TLSAdapter())
    res = session.get(url)
    result = json.loads(res.text)
    return result['Resident'][0].get('IdentifiantAdministratif')


# ----------------------------------------------------------------------------------------------------------------------
#
#             SECURISATION DES DOUBLONS NETSOINS VIA Nom, Prenom, DateNaissance et IdentifiantAdministratif
#                + CLE OBLIGATOIRE : IdentifiantExterne (clé unique par objet, utiliser ID de préférence)
#
# ----------------------------------------------------------------------------------------------------------------------
def post_cards(cards):
    url = get_netsoins_url_post('Resident')
    admin_id = get_administrative_id(cards.user_resident.profileserenicia.uri_netsoins)
    data = {
        "Nom": cards.user_resident.last_name,
        "Prenom": cards.user_resident.first_name,
        "IdentifiantAdministratif": admin_id,
        "DateNaissance": str(cards.user_resident.profileserenicia.birth_date) + 'T00:00:00+00:00',
        "IdentifiantExterne": cards.user_resident.id,
        "FichierInfoAdministratif": []
    }
    if cards.upload_mutual_card:
        data['FichierInfoAdministratif'].append({"IdentifiantExterne": "mutual_card" + str(cards.id),
                                                 "Nom": "mutual_card.jpg",
                                                 "Type": "jpg",
                                                 "Donnees": encode_to_base64(cards.upload_mutual_card.path)})
    if cards.upload_national_card:
        data['FichierInfoAdministratif'].append({"IdentifiantExterne": "national_card" + str(cards.id),
                                                 "Nom": "national_card.jpg",
                                                 "Type": "jpg",
                                                 "Donnees": encode_to_base64(cards.upload_national_card.path)})
    if cards.upload_attestation_vital_card:
        data['FichierInfoAdministratif'].append({"IdentifiantExterne": "attestation_vital_card" + str(cards.id),
                                                 "Nom": "attestation_vital_card.jpg",
                                                 "Type": "jpg",
                                                 "Donnees": encode_to_base64(
                                                     cards.upload_attestation_vital_card.path)})
    jsondata = json.dumps([data])
    try:
        session = requests.session()
        session.mount('https://', TLSAdapter())
        res = session.post(url, data=jsondata, timeout=60)
        ret = json.loads(res.text)
        log_cards.debug(f"POST card : {ret}")
    except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as err:
        log_cards.debug(f"POST card exception : {err}")
        raise Exception(err)


def cron_post_all_cards():
    listcard = Card.objects.all()
    for card in listcard:
        post_cards(card)
    log_cards.debug(f"post all cards, done.")


def test_post():
    c = Card.objects.get(user_resident__last_name='STEFF')
    url = get_netsoins_url_post('Resident')
    data = [{
        "Nom": "IPKISS",
        # "Prenom": "Stanley",
        # "IdentifiantAdministratif": '2626',
        # "DateNaissance": '2020-09-29T00:00:00+00:00',
        "IdentifiantExterne": "2626",
        "FichierInfoAdministratif": [{"IdentifiantExterne": "mutual_card2",
                                      "Nom": "mutual_card.jpg",
                                      "Type": "jpg",
                                      "Actif": 1,
                                      "Donnees": encode_to_base64(c.upload_mutual_card.path)
                                      }]
    }]
    jsondata = json.dumps(data)
    print("\ndata format json : ", jsondata)
    try:
        session = requests.session()
        session.mount('https://', TLSAdapter())
        res = session.post(url, data=jsondata, timeout=60)
        print("\nPOST !")
        print(res)
        ret = json.loads(res.text)
        print("\nretour de roquette :", ret)
    except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as err:
        raise Exception(err)


# Uri = comportement FK
def transmission_post():
    url = get_netsoins_url_post('Resident')
    print('url :', url)
    # pour GET transmission soin
    # transmission_dates = '&date_debut={}&date_fin={}&module={}'.format('2021-04-28', '', 1)
    uri_resident = quote_plus('teranga://demo.netsoins.org/Resident#351261.e3966f4a1f')
    uri_personnel = quote_plus('teranga://demo.netsoins.org/Personnel#395214.18b3f92f1c')
    data = [{
        "Nom": "IPKISS",
        "Prenom": "Stanley",
        "DateNaissance": "1989-05-16T00:00:00+01:00",
        "IdentifiantExterne": "testpostcreation1",
        "DernierDomicileCodePostal": 38840,
        # "UriResident": "teranga://demo.netsoins.org/Resident#351128.1debc8087c",
        # "Module": 1,
        # "DateDebut": "2021-06-15T00:00:00.0000",
        # "DateFin": "2021-06-15T14:30:00.0000",
        # "TransmissionMessage": [{"Message": "Clôture",
        #                          "Type": "NARRATIVE",
        #                          "Date": "2021-04-28T14:30:00.0000",
        #                          "UriPersonnel": "teranga://demo.netsoins.org/Personnel#395214.18b3f92f1c",
        #                          "IdentifiantExterne": "testposttransmissionmessageresultat2",
        #                         }]
    }]
    jsondata = json.dumps(data)
    print("\ndata format json : ", jsondata)
    try:
        session = requests.session()
        session.mount('https://', TLSAdapter())
        res = session.post(url, data=jsondata, timeout=60)
        print("\nPOST !")
        print(res)
        ret = json.loads(res.text)
        print("\nretour de roquette :", ret)
    except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as err:
        raise Exception(err)

# ----------------------------------------------------------------------------------------------------------------------


# Champs POST Resident disponibles pour Netsoin :

# [
#   {
#     "IdentifiantExterne": "string",
#     "Actif": 1,
#     "Archive": 1,
#     "Civilite": "MONSIEUR",
#     "Genre": "HOMME",
#     "Nom": "string",
#     "NomJeuneFille": "string",
#     "NomReligion": "string",
#     "Prenom": "string",
#     "Nationalite": "string",
#     "Telephone": "string",
#     "Mail": "string",
#     "DateNaissance": "2020-09-29T09:51:44.599Z",
#     "CodePostalNaissance": "string",
#     "VilleNaissance": "string",
#     "IdentifiantDepartementNaissance": 11,
#     "IdentifiantPaysNaissance": "004",
#     "SituationFamiliale": "CELIBATAIRE",
#     "UriResidentCouple": "string",
#     "IdentifiantAdministratif": "string",
#     "ResidentPieceIdentite": [
#       {
#         "IdentifiantExterne": "string",
#         "Actif": 1,
#         "TypePieceIdentite": "CARTE_IDENTITE",
#         "UriPersonnel": "string",
#         "Date": "2020-09-29T09:51:44.599Z",
#         "DateDemande": "2020-09-29T09:51:44.599Z",
#         "DateDebut": "2020-09-29T09:51:44.599Z",
#         "DateFin": "2020-09-29T09:51:44.599Z",
#         "Numero": "string",
#         "DemandeEnCours": 0,
#         "DelivrerPar": "string",
#         "Commentaire": "string",
#         "FichierInfo": [
#           {
#             "IdentifiantExterne": "string",
#             "Actif": 1,
#             "Nom": "string",
#             "Type": "string",
#             "Donnees": "Unknown Type: base64Binary"
#           }
#         ]
#       }
#     ],
#     "AccordReglement": 0,
#     "DateAccordReglement": "2020-09-29T09:51:44.600Z",
#     "AssuranceResponsabiliteCivile": "string",
#     "NumeroAssuranceResponsabiliteCivile": "string",
#     "DateDebutAssuranceResponsabiliteCivile": "2020-09-29T09:51:44.600Z",
#     "DateFinAssuranceResponsabiliteCivile": "2020-09-29T09:51:44.600Z",
#     "CommentaireContrat": "string",
#     "ProvenanceIdentifiantProximite": "AGGLOMERATION",
#     "ProvenanceProximiteIdentifiantPays": "004",
#     "IdentifiantProvenance": "FAMILLE",
#     "ProvenanceFiness": "string",
#     "ProvenanceLibelle": "string",
#     "ProvenanceAdresse": "string",
#     "ProvenanceCodePostal": "string",
#     "ProvenanceVille": "string",
#     "ProvenanceIdentifiantDepartement": 11,
#     "ProvenanceIdentifiantPays": "004",
#     "ProvenanceTelephoneFixe": "string",
#     "ProvenanceAutreTelephoneFixe": "string",
#     "IdentifiantModeResidence": "AUCUN",
#     "DernierDomicileAdresse": "string",
#     "DernierDomicileCodePostal": "string",
#     "DernierDomicileVille": "string",
#     "DernierDomicileIdentifiantDepartement": 11,
#     "DernierDomicileIdentifiantPays": "004",
#     "DernierDomicileTelephoneFixe": "string",
#     "DernierDomicileAutreTelephoneFixe": "string",
#     "DomicileSecoursAdresse": "string",
#     "DomicileSecoursCodePostal": "string",
#     "DomicileSecoursVille": "string",
#     "DomicileSecoursIdentifiantDepartement": 11,
#     "DomicileSecoursIdentifiantPays": "004",
#     "DomicileSecoursTelephoneFixe": "string",
#     "DomicileSecoursAutreTelephoneFixe": "string",
#     "ResidentSecuriteSociale": [
#       {
#         "IdentifiantExterne": "string",
#         "Actif": 1,
#         "UriSecuriteSociale": "string",
#         "DateDebut": "2020-09-29T09:51:44.600Z",
#         "DateFin": "2020-09-29T09:51:44.600Z",
#         "NumeroSecuriteSociale": "string",
#         "PetitRegime": "string",
#         "CodeBeneficiaire": "ASSURE",
#         "Nom": "string",
#         "Prenom": "string",
#         "Justificatif": "string",
#         "Adresse": "string",
#         "CodePostal": "string",
#         "Ville": "string",
#         "IdentifiantPays": "004",
#         "Commentaire": "string",
#         "FichierInfo": [
#           {
#             "IdentifiantExterne": "string",
#             "Actif": 1,
#             "Nom": "string",
#             "Type": "string",
#             "Donnees": "Unknown Type: base64Binary"
#           }
#         ]
#       }
#     ],
#     "ResidentMutuelle": [
#       {
#         "IdentifiantExterne": "string",
#         "Actif": 1,
#         "UriMutuelle": "string",
#         "DateDebut": "2020-09-29T09:51:44.600Z",
#         "DateFin": "2020-09-29T09:51:44.600Z",
#         "ValiditePermanente": 0,
#         "Numero": "string",
#         "Principale": 0,
#         "Commentaire": "string",
#         "FichierInfo": [
#           {
#             "IdentifiantExterne": "string",
#             "Actif": 1,
#             "Nom": "string",
#             "Type": "string",
#             "Donnees": "Unknown Type: base64Binary"
#           }
#         ]
#       }
#     ],
#     "ResidentCaisse": [
#       {
#         "IdentifiantExterne": "string",
#         "Actif": 1,
#         "UriCaisse": "string",
#         "Principale": 0,
#         "DateDebut": "2020-09-29T09:51:44.600Z",
#         "DateFin": "2020-09-29T09:51:44.600Z",
#         "ValiditePermanente": 0
#       }
#     ],
#     "ResidentAide": [
#       {
#         "IdentifiantExterne": "string",
#         "Actif": 1,
#         "IdentifiantTypeAide": "ACS",
#         "DateDemande": "2020-09-29T09:51:44.600Z",
#         "DateDebut": "2020-09-29T09:51:44.600Z",
#         "DateFin": "2020-09-29T09:51:44.600Z",
#         "DateRetroactivite": "2020-09-29T09:51:44.600Z",
#         "NumeroDossier": "string",
#         "Commentaire": "string",
#         "AideLogementMontant": 0,
#         "AideLogementIdentifiantTypeAideLogement": "APL",
#         "AideLogementIdentifiantTypeVersement": "RESIDENT",
#         "AideSocialeIdentifiantTypeAideSociale": "HEBERGEMENT_UNIQUEMENT",
#         "AideSocialeDateRemise": "2020-09-29T09:51:44.600Z",
#         "AideSocialeDateAcceptation": "2020-09-29T09:51:44.600Z",
#         "AideSocialeResteACharge": 0,
#         "AideSocialePecule": 0,
#         "AideSocialePeculeMontant": 0,
#         "AideSocialePeculePourcent": 0,
#         "AideSocialeReversementConseilGeneral": 0,
#         "AideSocialeIdentifiantTypeVersement": "RESIDENT",
#         "APAMontant": 0,
#         "APAFrequence": "string",
#         "APAIdentifiantTypeVersement": "CALCUL_ETABLISSEMENT",
#         "Departement": "string",
#         "FichierInfo": [
#           {
#             "IdentifiantExterne": "string",
#             "Actif": 1,
#             "Nom": "string",
#             "Type": "string",
#             "Donnees": "Unknown Type: base64Binary"
#           }
#         ]
#       }
#     ],
#     "DerogationGIR60": 0,
#     "DroitVote": 0,
#     "DroitVoteCommentaire": "string",
#     "ResidentPraticien": [
#       {
#         "IdentifiantExterne": "string",
#         "UriPersonnel": "string",
#         "MedecinTraitant": 0,
#         "PharmacienTraitant": 0,
#         "Referent": 0,
#         "Kine": 0,
#         "Commentaire": "string"
#       }
#     ],
#     "OrganismePompeFunebre": "string",
#     "NumeroContratObseques": "string",
#     "Cremation": 0,
#     "PaceMaker": 0,
#     "DateControlePaceMaker": "2020-09-29T09:51:44.600Z",
#     "CommentairePaceMaker": "string",
#     "CommentaireAuQuotidien": "string",
#     "CommentaireInformationsGenerales": "string",
#     "ResidentContact": [
#       {
#         "IdentifiantExterne": "string",
#         "Actif": 1,
#         "IdentifiantAdministratif": "string",
#         "LienParente": "PERE_MERE",
#         "Civilite": "MONSIEUR",
#         "Genre": "HOMME",
#         "Nom": "string",
#         "NomJeuneFille": "string",
#         "NomReligion": "string",
#         "Prenom": "string",
#         "DateNaissance": "2020-09-29T09:51:44.600Z",
#         "CodePostalNaissance": "string",
#         "VilleNaissance": "string",
#         "IdentifiantDepartementNaissance": 11,
#         "IdentifiantPaysNaissance": "004",
#         "Adresse": "string",
#         "CodePostal": "string",
#         "Ville": "string",
#         "IdentifiantDepartement": 11,
#         "IdentifiantPays": "004",
#         "Mail": "string",
#         "TelephoneFixe": "string",
#         "AutreTelephoneFixe": "string",
#         "TelephoneProfessionnel": "string",
#         "TelephoneMobile": "string",
#         "AutreTelephoneMobile": "string",
#         "TelephoneVacances": "string",
#         "Fax": "string",
#         "PrevenirLaNuit": 1,
#         "ReferentFamilial": 1,
#         "PersonneDeConfiance": 1,
#         "Commentaire": "string",
#         "OrdreAppel": 0,
#         "TypeRelationAutre": "string",
#         "FichierInfo": [
#           {
#             "IdentifiantExterne": "string",
#             "Actif": 1,
#             "Nom": "string",
#             "Type": "string",
#             "Donnees": "Unknown Type: base64Binary"
#           }
#         ],
#         "DestinataireFacture": true,
#         "CautionSolidaire": true
#       }
#     ],
#     "ResidentInventaire": [
#       {
#         "IdentifiantExterne": "string",
#         "UriInventaire": "string",
#         "Prix": 0,
#         "Commentaire": "string",
#         "TrousseauHospitalisation": 0,
#         "UriPersonnel": "string"
#       }
#     ],
#     "CompteTiers": "string",
#     "CompteAuxiliaire": "string",
#     "FacturationCouple": 1,
#     "FacturationAdresse": "string",
#     "FacturationCodePostal": "string",
#     "FacturationVille": "string",
#     "FacturationIdentifiantDepartement": 11,
#     "FacturationIdentifiantPays": "004",
#     "FacturationTelephoneFixe": "string",
#     "FacturationAutreTelephoneFixe": "string",
#     "FacturationCommentaire": "string",
#     "FacturationCommentaireFacture": "string",
#     "FacturationDateDebutCommentaireFacture": "2020-09-29T09:51:44.600Z",
#     "FacturationDateFinCommentaireFacture": "2020-09-29T09:51:44.600Z",
#     "ModeReglement": "ACOMPTE",
#     "ModeReglementTitulaire": "string",
#     "UriBanqueModeReglement": "string",
#     "ModeReglementBic": "string",
#     "ModeReglementRib": "string",
#     "ModeReglementIban": "string",
#     "ModeReglementJourEcheance": 0,
#     "ModeReglementDateAutorisation": "2020-09-29T09:51:44.600Z",
#     "ModeReglementIdentifiantComptableSEPA": "string",
#     "Mandat": [
#       {
#         "IdentifiantExterne": "string",
#         "Actif": 1,
#         "Rum": "string",
#         "Date": "2020-09-29T09:51:44.600Z",
#         "ModeReglement": "ACOMPTE",
#         "ModeReglementTitulaire": "string",
#         "UriBanqueModeReglement": "string",
#         "ModeReglementBic": "string",
#         "ModeReglementRib": "string",
#         "ModeReglementIban": "string",
#         "ModeReglementJourEcheance": 0,
#         "ModeReglementDateAutorisation": "2020-09-29T09:51:44.600Z",
#         "ModeReglementIdentifiantComptableSEPA": "string",
#         "Recurrent": 1,
#         "DatePremier": "2020-09-29T09:51:44.600Z",
#         "IdentifiantComptableMandat": "string",
#         "IdentifiantExterneResidentContact": "string"
#       }
#     ],
#     "ResidentDebiteur": [
#       {
#         "IdentifiantExterne": "string",
#         "Actif": 1,
#         "Montant": "string",
#         "Pourcentage": "string",
#         "ModeParticipation": "MODE_MONTANT",
#         "PosteParticipation": "POSTE_RESTEACHARGE",
#         "DateDebut": "2020-09-29T09:51:44.600Z",
#         "DateFin": "2020-09-29T09:51:44.600Z",
#         "Ordre": "string",
#         "CompteTiers": "string",
#         "CompteAnalytique": "string",
#         "CompteAuxiliaire": "string",
#         "Commentaire": "string",
#         "ModeReglement": "ACOMPTE",
#         "ReglementTitulaire": "string",
#         "UriReglementBanque": "string",
#         "ReglementNumero": "string",
#         "ReglementIban": "string",
#         "ReglementBic": "string",
#         "ReglementJourEcheance": 0,
#         "ReglementDateAutorisation": "2020-09-29T09:51:44.600Z",
#         "ReglementIdentifiantComptable": "string",
#         "IdentifiantExterneResidentContact": "string"
#       }
#     ],
#     "ResidentPathologie": [
#       {
#         "IdentifiantExterne": "string",
#         "UriPathologie": "string",
#         "Commentaire": "string",
#         "DateDebut": "2020-09-29T09:51:44.600Z",
#         "DateFin": "2020-09-29T09:51:44.600Z",
#         "Fini": 0,
#         "UriPersonnel": "string",
#         "DansEtablissement": 0,
#         "Antecedent": "CHIRURGICAL"
#       }
#     ],
#     "ResidentAld": [
#       {
#         "IdentifiantExterne": "string",
#         "UriPathologie": "string",
#         "ValiditePermanente": 0,
#         "DateDebut": "2020-09-29T09:51:44.600Z",
#         "DateFin": "2020-09-29T09:51:44.600Z",
#         "TypeAld": "CNAM",
#         "Commentaire": "string"
#       }
#     ],
#     "ResidentHypersensibilite": [
#       {
#         "IdentifiantExterne": "string",
#         "UriHypersensibilite": "string",
#         "Commentaire": "string",
#         "DateDebut": "2020-09-29T09:51:44.600Z",
#         "DateFin": "2020-09-29T09:51:44.600Z",
#         "Fini": 0,
#         "UriPersonnel": "string",
#         "Alimentaire": 0
#       }
#     ],
#     "ResidentVaccin": [
#       {
#         "IdentifiantExterne": "string",
#         "UriVaccin": "string",
#         "Date": "2020-09-29T09:51:44.600Z",
#         "NumeroLot": "string",
#         "Commentaire": "string",
#         "PriseEnCharge": "NON",
#         "StopAlerte": 0,
#         "Refuse": 0,
#         "UriPersonnel": "string"
#       }
#     ],
#     "ResidentBacterie": [
#       {
#         "IdentifiantExterne": "string",
#         "UriBacterie": "string",
#         "UriProtocole": "string",
#         "Commentaire": "string",
#         "DateDebut": "2020-09-29T09:51:44.600Z",
#         "DateFin": "2020-09-29T09:51:44.600Z",
#         "Fini": 0,
#         "UriPersonnel": "string",
#         "DansEtablissement": 0,
#         "Precaution": 0,
#         "PrecautionAir": 0,
#         "PrecautionGouttelette": 0,
#         "PrecautionContact": 0
#       }
#     ],
#     "ResidentRisque": [
#       {
#         "IdentifiantExterne": "string",
#         "UriRisque": "string",
#         "Commentaire": "string",
#         "DateDebut": "2020-09-29T09:51:44.600Z",
#         "DateFin": "2020-09-29T09:51:44.600Z"
#       }
#     ],
#     "ResidentRegime": [
#       {
#         "IdentifiantExterne": "string",
#         "UriTypeRegime": "string",
#         "Commentaire": "string",
#         "DateDebut": "2020-09-29T09:51:44.600Z",
#         "DateFin": "2020-09-29T09:51:44.600Z",
#         "UriPersonnel": "string"
#       }
#     ],
#     "ResidentTexture": [
#       {
#         "IdentifiantExterne": "string",
#         "UriTexture": "string",
#         "UriTextureComplement": "string",
#         "Date": "2020-09-29T09:51:44.600Z",
#         "DateDebut": "2020-09-29T09:51:44.600Z",
#         "DateFin": "2020-09-29T09:51:44.600Z",
#         "Commentaire": "string",
#         "UriPersonnel": "string"
#       }
#     ],
#     "ResidentModeAlimentation": [
#       {
#         "IdentifiantExterne": "string",
#         "UriModeAlimentation": "string",
#         "Commentaire": "string",
#         "Date": "2020-09-29T09:51:44.600Z",
#         "DateDebut": "2020-09-29T09:51:44.600Z",
#         "DateFin": "2020-09-29T09:51:44.600Z",
#         "UriPersonnel": "string"
#       }
#     ],
#     "ResidentComplementAliment": [
#       {
#         "IdentifiantExterne": "string",
#         "UriTypeComplementAlimentaire": "string",
#         "UriComplementAlimentaireForme": "string",
#         "Commentaire": "string",
#         "Date": "2020-09-29T09:51:44.600Z",
#         "UriPersonnel": "string",
#         "DateDebut": "2020-09-29T09:51:44.600Z",
#         "DateFin": "2020-09-29T09:51:44.600Z",
#         "FormeAutre": "string"
#       }
#     ],
#     "ResidentBoisson": [
#       {
#         "IdentifiantExterne": "string",
#         "UriTypeBoisson": "string",
#         "UriPersonnel": "string",
#         "Date": "2020-09-29T09:51:44.600Z",
#         "DateDebut": "2020-09-29T09:51:44.600Z",
#         "DateFin": "2020-09-29T09:51:44.600Z",
#         "Commentaire": "string"
#       }
#     ],
#     "BonneHydratation": 0,
#     "BoitSeule": 0,
#     "StimulationPourBoire": 0,
#     "HydratationCommentaire": "string",
#     "AlimentationAlcool": 0,
#     "Douloureux": 0,
#     "TroubleHumeurComportement": 0,
#     "AnomaliePied": 0,
#     "TroubleSensibilite": 0,
#     "Sourd": 0,
#     "AppareilAuditif": 0,
#     "Malvoyant": 0,
#     "AppareilVisuel": 0,
#     "MobiliteReduite": 0,
#     "TypeAideTechnique": "AUCUNE",
#     "Desorientation": 0,
#     "Deambulant": 0,
#     "AidePriseMedicament": 0,
#     "TraitementsEcrases": 0,
#     "AideAlimentaire": 0,
#     "TroubleDeglutition": 0,
#     "ResidentTransfusion": [
#       {
#         "IdentifiantExterne": "string",
#         "Commentaire": "string",
#         "DateFait": "2020-09-29T09:51:44.600Z",
#         "DateSaisie": "2020-09-29T09:51:44.600Z",
#         "UriPersonnel": "string"
#       }
#     ],
#     "DerniereProfession": "string",
#     "NombreEnfantsTotal": 0,
#     "NombreEnfantsDecedes": 0,
#     "ResidentConsentement": [
#       {
#         "IdentifiantExterne": "string",
#         "Actif": 1,
#         "ConstanteConsentement": "TELEMEDECINE",
#         "ConstanteAccord": "NON",
#         "UriPersonnel": "string",
#         "UriPersonnelReccueillant": "string",
#         "Date": "2020-09-29T09:51:44.600Z",
#         "DateAccord": "2020-09-29T09:51:44.600Z",
#         "Commentaire": "string",
#         "FichierInfo": [
#           {
#             "IdentifiantExterne": "string",
#             "Actif": 1,
#             "Nom": "string",
#             "Type": "string",
#             "Donnees": "Unknown Type: base64Binary"
#           }
#         ]
#       }
#     ],
#     "Photo": {
#       "IdentifiantExterne": "string",
#       "Actif": 1,
#       "Nom": "string",
#       "Type": "string",
#       "Donnees": "Unknown Type: base64Binary"
#     },
#     "FichierInfo": [
#       {
#         "IdentifiantExterne": "string",
#         "Actif": 1,
#         "Nom": "string",
#         "Type": "string",
#         "Donnees": "Unknown Type: base64Binary"
#       }
#     ],
#     "FichierInfoMedical": [
#       {
#         "IdentifiantExterne": "string",
#         "Actif": 1,
#         "Nom": "string",
#         "Type": "string",
#         "Donnees": "Unknown Type: base64Binary"
#       }
#     ],
#     "FichierInfoFacturation": [
#       {
#         "IdentifiantExterne": "string",
#         "Actif": 1,
#         "Nom": "string",
#         "Type": "string",
#         "Donnees": "Unknown Type: base64Binary"
#       }
#     ],
#     "FichierInfoProjetDeVie": [
#       {
#         "IdentifiantExterne": "string",
#         "Actif": 1,
#         "Nom": "string",
#         "Type": "string",
#         "Donnees": "Unknown Type: base64Binary"
#       }
#     ],
#     "FichierInfoAlimentation": [
#       {
#         "IdentifiantExterne": "string",
#         "Actif": 1,
#         "Nom": "string",
#         "Type": "string",
#         "Donnees": "Unknown Type: base64Binary"
#       }
#     ],
#     "FichierInfoAdministratif": [
#       {
#         "IdentifiantExterne": "string",
#         "Actif": 1,
#         "Nom": "string",
#         "Type": "string",
#         "Donnees": "Unknown Type: base64Binary"
#       }
#     ],
#     "ResidentContrat": [
#       {
#         "IdentifiantExterne": "string",
#         "Actif": 1,
#         "NomContrat": "string",
#         "PrenomContrat": "string",
#         "Date": "2020-09-29T09:51:44.600Z",
#         "DateDebut": "2020-09-29T09:51:44.600Z",
#         "DateFinFacturation": "2020-09-29T09:51:44.600Z",
#         "DateVersement": "2020-09-29T09:51:44.600Z",
#         "ModeVersement": "CHEQUE",
#         "TypeContrat": "CONTRAT_DE_SOUTIEN_ET_D_AIDE_PAR_LE_TRAVAIL",
#         "TypeContratSejour": "HEBERGEMENT_TEMPORAIRE",
#         "TitulaireCompte": "string",
#         "JoursPreavis": "string",
#         "Terme": "string",
#         "MontantHT": 0,
#         "MontantTTC": 0,
#         "MontantTTCReservation": 0,
#         "MontantTTCMoins60Ans": 0,
#         "MontantTTCReservation60": 0,
#         "ModeTTC": "string",
#         "UriArticle": "string",
#         "MontantArticleForfaitJournalier": 0,
#         "MontantArticleForfaitHospitalier": 0,
#         "MontantArticleForfaitPsy": 0,
#         "UriBanque": "string",
#         "UriConseilGeneralDependance": "string",
#         "SansDependance": 0,
#         "NumeroCheque": "string",
#         "Commentaire": "string",
#         "CommentaireRestitution": "string",
#         "MontantRestitution": 0,
#         "DateRestitution": "2020-09-29T09:51:44.600Z",
#         "PrixFacture": 0,
#         "DelaiRestitution": 0,
#         "FichierInfo": [
#           {
#             "IdentifiantExterne": "string",
#             "Actif": 1,
#             "Nom": "string",
#             "Type": "string",
#             "Donnees": "Unknown Type: base64Binary"
#           }
#         ]
#       }
#     ],
#     "ResidentArticle": [
#       {
#         "IdentifiantExterne": "string",
#         "Actif": 1,
#         "UriArticle": "string",
#         "Quantite": 0,
#         "MontantUnitaireTTC": 0,
#         "Frequence": "PONCTUEL",
#         "DateDebut": "2020-09-29T09:51:44.600Z",
#         "DateFin": "2020-09-29T09:51:44.600Z",
#         "Presentiel": 1,
#         "CarenceHospitalisation": 0,
#         "CarenceVacances": 0,
#         "AideSociale": 1,
#         "Commentaire": "string"
#       }
#     ],
#     "AlimentationInterdit": "string",
#     "ResidentQuantiteRepas": [
#       {
#         "IdentifiantExterne": "string",
#         "UriMomentRepas": "string",
#         "Quantite": "NORMAL",
#         "Commentaire": "string"
#       }
#     ],
#     "PriseDuRepas": "AUTONOME",
#     "AlimentationAccompagnement": 0,
#     "RepasCommentaireAutonomie": "string",
#     "AdresseEtablissementFacturation": 0
#   }
# ]
