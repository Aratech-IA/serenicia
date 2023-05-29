import json
import sys
import os

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

from django.contrib.auth.models import Group, Permission


def import_groups():
    with open('app0_access/fixtures/groups.json', 'rb') as f:
        for values in json.load(f):
            grp = Group.objects.get_or_create(name=values['name'])[0]
            perms = Permission.objects.filter(content_type__app_label=values['permissions__content_type__app_label'],
                                              content_type__model=values['permissions__content_type__model'])
            grp.permissions.add(*perms)


def log_groups():
    for grp in Group.objects.all():
        print(f'{grp.name} - {grp.permissions.count()} permissions')


if __name__ == '__main__':
    import_groups()
    log_groups()
