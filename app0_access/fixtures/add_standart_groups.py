import sys
import os

# ------------------------------------------------------------------------------
# Because this script have to be run in a separate process from manage.py
# you need to set up a Django environnement to use the Class defined in
# the Django models. It is necesssary to interact witht the Django database
# ------------------------------------------------------------------------------
# to get the projet.settings it is necessary to add the parent directory
# to the python path
try:
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
except NameError:
    sys.path.append(os.path.abspath('..'))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "projet.settings.settings")
import django
django.setup()

from django.contrib.auth.models import Group, Permission

user_type_per_group = {
    'view_as': ['AMP', 'AES', 'AS', ],
    'view_ash': ["Responsable d'hébergement", 'ASH', 'Agent de service technique', ],
    'view_ide': ['Infirmier/ère', 'IDEC'],
    'view_family': ['Famille'],
    'view_prospect': ['Mass Mailing', ],
    'view_practicians': ['Psychomotricienne', 'Pédicure - podologue', 'Orthophoniste',
                         'Kinésithérapeute', 'Ergothérapeute', 'Médecin - Généraliste', 'Médecin - Dentiste', ],
    'view_residentehpad': ['Résident EHPAD'],
    'view_residentrss': ['Résident RSS'],
    'view_manager': ['Direction', ],
    'view_otheremployee': ['Chef Cuisine', 'Responsable cuisine', 'Cuisinier/ère', 'Administratif', 'Gestion paye',
                           'Psychologue', ],
    'view_otherextern': ['Ambulance - Taxi - VSL', 'Coiffeur/feuse', 'Pharmacie', 'Socio-esthéticienne',
                         'Delivery Business', 'Customer Delivery', 'Delivery Man', 'Informaticien'],
                 }

for perm, groups in user_type_per_group.items():
    for group in groups:
        new_group, created = Group.objects.get_or_create(name=group)
        permission = Permission.objects.get(codename=perm)
        new_group.permissions.add(permission)
        # new_group.permissions.clear()
