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

from app4_ehpad_base.api_google import check_service_account, check_calendar

check_service_account()
check_calendar()

# WARNING this script need an api google settled on google console ##
# 3 api should be enable on google api console 
# IAM Service Account Credentials API
# Identity and Access Management (IAM) API
# Google Cloud Storage JSON API
# the first service account member aaa_prod_ehpad0 must be an owner for permission
