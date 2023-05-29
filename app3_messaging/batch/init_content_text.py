import os
import sys

try:
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
except NameError:
    sys.path.append(os.path.abspath('../..'))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "projet.settings.settings")

import django
django.setup()
from app3_messaging.models import IntraEmail
from app3_messaging.textprocess import htmltotext

all_messages = IntraEmail.objects.all()
for message in all_messages:
    message.content_text = htmltotext(message.content)
    message.save()
