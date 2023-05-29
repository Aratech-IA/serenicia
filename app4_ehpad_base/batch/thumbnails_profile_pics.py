"""This program aim to resize all the profile pictures with max height or widht at 200px.
It's a one shot program"""

import glob
from PIL import Image, UnidentifiedImageError
import os

path = '/App/media_root/residents/*/profile_pics/*.jpg'

folders = glob.glob(path)

for picture in folders:
    try:
        img = Image.open(picture)
        img.thumbnail((200, 200))
        img.convert('RGB').save(picture)

    except UnidentifiedImageError:
        os.remove(picture)
