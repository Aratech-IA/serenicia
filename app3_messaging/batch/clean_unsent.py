import sys
import os

try:
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
except NameError:
    sys.path.append(os.path.abspath('../..'))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "projet.settings.settings")
# noinspection PyPep8
import django
django.setup()

from app3_messaging.textprocess import cleaning_unsent

cleaning_unsent()
