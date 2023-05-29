
import sys
import os

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

import glob
import logging
from datetime import datetime as dt
from time import perf_counter
from app1_base.log import Logger

from app4_ehpad_base.models import ProfileSerenicia

if 'log_picscount' not in globals():
    global log_picscount
    log_picscount = Logger('picscount', level=logging.ERROR).run()

path = '/App/media_root/residents/'
now = dt.now()
folders = glob.glob(path + '*')
log_picscount.info(f"log from : {dt.now()}")
for folder in folders:
    start_1 = perf_counter()
    counter = 0
    files = glob.glob(folder + '/*.jpg')
    for pict in files:
        try:
            res = now - dt.strptime(pict.split('/')[-1][:10], '%Y-%m-%d')
            if res.days <= 7:
                counter += 1
        except ValueError:
            log_picscount.debug(f"unkonwn date : {pict}\n")
    try:
        obj = ProfileSerenicia.objects.get(folder=folder.split('/')[-1])
        obj.pics_total = len(files)
        obj.pics_last = counter
        obj.save()
    except ProfileSerenicia.DoesNotExist:
        log_picscount.debug(f"unkonwn ProfileSerenicia : {folder.split('/')[-1]}\n")
