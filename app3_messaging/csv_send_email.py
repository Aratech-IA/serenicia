import csv
import sys
import os
import logging
import time

# Because this script have to be run in a separate process from manage.py
# you need to set up a Django environnement to use the Class defined in
# the Django models. It is necesssary to interact witht the Django database
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

from app1_base.models import User
from app1_base.models import Profile
from app3_messaging.models import ProfileProspect
from app1_base.log import Logger
from django.contrib.auth.models import Group


if 'log_csv' not in globals():
    log_csv = Logger('csv', level=logging.WARNING, file=False).run()


def csv_get_data(file_path_of_csv):
    """
        :param file_path_of_csv: Path of the .csv file. Is a string.
    """

    list_element = []
    with open(file_path_of_csv) as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=',')
        line_count = 0
        for row in csv_reader:
            if line_count == 0:
                names = row
                line_count += 1
            else:
                element = {}
                for name in names:  # pour chaques noms de colonnes
                    element[name] = row[names.index(name)]
                list_element.append(element)
                line_count += 1
            # if line_count == 5:  # should be used when testing only
            #     break
    return list_element


def create_user_with_list(liste, groupname):
    """
        :param liste: liste de dicos
        :param groupname: nom d'un groupe EXISTANT renvoi une erreur sinon.
    """

    inc = 0
    allgroups = Group.objects.all()
    allgroupsname = []
    list_element_user = ['first_name', 'last_name', 'username', 'email']
    list_element_profile = ["adress", "phone_number", "cp", "city", "civility"]
    list_element_profile_prospect = ["finess", "name", "capacity", "status", "dept_name", "dept_code",
                                     "gestionnaire", "info_presta", "info_tarif", "function"]
    for g in allgroups:
        allgroupsname.append(g.name)
    if groupname in allgroupsname:
        for dico in liste:
            list_accepted_element = []
            list_accepted_element_prospect = []
            dico = {key: value for key, value in dico.items() if value is not None and value != ""}
            # remove empty element from dico, but does not actually remove them from the list
            dico_profile = {}
            dico_profile_prospect = {}
            correct = False
            log_csv.debug(f'dico is {dico} \n')
            for element in dico:  # pour chaques clés dans le dico
                if "email" in element:  # si la clé a pour valeure un email:
                    if "@" and "." in dico[element]:  # si un @ et un . est dans la supposé adresse email:
                        correct = True
                    else:
                        pass
                for name in list_element_profile:
                    if name == element:
                        log_csv.debug(f'{name} is in  {element} \n')
                        list_accepted_element.append(name)
                for name in list_element_profile_prospect:
                    if name == element:
                        list_accepted_element_prospect.append(name)
            if correct:
                log_csv.debug(f'list_accepted_element -> {list_accepted_element}\n')
                for field in list_accepted_element:
                    log_csv.debug(f'process field {field}\n')
                    log_csv.debug(f'in dico {dico}\n')
                    dico_profile[field] = dico[field]
                    dico.pop(field)
                for field in list_accepted_element_prospect:
                    dico_profile_prospect[field] = dico[field]
                    dico.pop(field)
                dico = {key: value for (key, value) in dico.items() if key in list_element_user}
                log_csv.debug(f'before update or create {dico} ')
                try:
                    obj, created = User.objects.update_or_create(username=dico["email"], email=dico["email"], defaults=dico)
                    log_csv.debug(f'after update or create obj --> {obj}  created --> {created}')
                    user = User.objects.get(username=dico["email"])
                    Profile.objects.update_or_create(user=user, defaults=dico_profile)
                    ProfileProspect.objects.update_or_create(user=user, defaults=dico_profile_prospect)
                    group = Group.objects.get(name=groupname)
                    group.user_set.add(user)
                    group.save()
                except Exception as e:
                    log_csv.error(f'exception in user data, type : {e.__class__.__name__} --> {e}')
                    time.sleep(1)

                log_csv.warning(f'prospect n° {inc} --> {dico["email"]} was {created}')
                inc += 1
    else:
        raise ValueError(groupname, "is not an existing group :/")

    return print("Created ", inc, "new Users in the group ", groupname)


def csv_to_user(file_path_of_csv, groupname="prospect"):
    liste = csv_get_data(file_path_of_csv)
    create_user_with_list(liste, groupname)


if __name__ == "__main__":
    # execute only if run as a script
    csv_to_user(sys.argv[1])
