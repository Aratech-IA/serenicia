import sys
import os

try:
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
except NameError:
    sys.path.append(os.path.abspath('..'))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "projet.settings.settings")
import django
django.setup()
from django.conf import settings

if "serenicia" in settings.DOMAIN.lower():
    from app4_ehpad_base.models import PreferencesSerenicia
from app1_base.models import Preferences, Profile


profiles = Profile.objects.exclude(user__groups__permissions__codename__in=['view_prospect', ])
for profile in profiles:
    obj, created = Preferences.objects.get_or_create(profile=profile)
    # print(obj.id, obj.profile.user.username)
    obj.save()
    if "serenicia" in settings.DOMAIN.lower():
        obj_j, created_j = PreferencesSerenicia.objects.get_or_create(profile=profile)
        # print("Pref: ", obj.id, created, "|", "Pref J: ", obj_j.id, created_j, "|", obj.profile.user.username)
        obj_j.save()
