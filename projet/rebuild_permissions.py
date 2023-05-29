import sys
import os

try:
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
except NameError:
    sys.path.append(os.path.abspath('../'))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "projet.settings.settings")
# noinspection PyPep8
import django
django.setup()

from django.apps.registry import apps
from django.contrib.contenttypes.management import create_contenttypes
from django.contrib.auth.management import create_permissions

list_apps = [app.name.split('.')[-1] for app in apps.get_app_configs()]


for app in reversed(list_apps):
    app_config = apps.get_app_config(app)

    # To create Content Types
    create_contenttypes(app_config)

    # To create Permissions
    create_permissions(app_config)
