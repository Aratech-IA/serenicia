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

from django.contrib.auth.models import Group


def export_groups():
    groups = Group.objects.all()
    with open('app0_access/fixtures/groups.json', 'w') as f:
        json.dump(list(groups.values('name', 'permissions__content_type__app_label',
                                        'permissions__content_type__model').distinct('permissions__content_type__app_label',
                                                                                     'permissions__content_type__model',
                                                                                     'name')), f)
    return groups.count()


if __name__ == '__main__':
    count = export_groups()
    print(f'{count} groupes ont été exportés dans app0_access/fixtures/groups.json')
