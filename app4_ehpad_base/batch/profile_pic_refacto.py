import os
import sys

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

from app4_ehpad_base.models import ProfileSerenicia
import glob
from PIL import Image

pictures = glob.glob('/App/media_root/residents/*/profile_pics/profile_pic.jpg')
print(len(pictures))
for picture in pictures:
    print(picture)
    img = Image.open(picture)
    print('image open')
    img.convert('RGB').save('/App/media_root/users_photo/' + picture.split('/')[-3] + '.jpg')
    print('image save')

print('rezising ...')
profiles = glob.glob('/App/media_root/users_photo/*.jpg')
print(len(profiles))
for profil in profiles:
    print(profil)
    img2 = Image.open(profil)
    img2.thumbnail((200, 200))
    print('convert to thumbnail')
    img2.convert('RGB').save(profil)
    print('saving')
    ProfileSerenicia.objects.filter(folder=profil.split('.')[-2].split('/')[-1]).update(
        photo='users_photo/' + profil.split('/')[-1])
    print('database update ok')

print('done')
