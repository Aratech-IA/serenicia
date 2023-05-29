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

from app4_ehpad_base.models import ProfileSerenicia
from app1_base.models import Profile

pjs = ProfileSerenicia.objects.filter(user__profile__isnull=False)
for pj in pjs:
    if pj.photo:
        profile = pj.user.profile
        print(pj.user.username, '\n', pj.photo)
        profile.photo = pj.photo
        print(profile.photo)
        print('----------------')
        profile.save()


