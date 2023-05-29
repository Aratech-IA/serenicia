import json

import requests
from asgiref.sync import sync_to_async
from django.conf import settings

from app4_ehpad_base.models import ProfileSerenicia


def _add_profileserenicia_to_m2m(folder, m2m):
    m2m.add(ProfileSerenicia.objects.get(folder=folder))


async def identifying_multifaces_photo(file, m2m):
    # answer = requests.post(settings.FACIAL_RECO_MULTI, data=file)
    # list_folder = json.loads(answer.text)
    # [await sync_to_async(_add_profileserenicia_to_m2m, thread_sensitive=True)(folder, m2m)
    # for folder in list_folder]
    pass
