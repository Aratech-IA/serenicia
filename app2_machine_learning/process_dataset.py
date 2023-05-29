# -*- coding: utf-8 -*-
"""
Created on Sun Apr 14 21:29:53 2019

@author: julien
"""

import os
import glob
import sys
from django.conf import settings

#------------------------------------------------------------------------------
# Because this script have to be run in a separate process from manage.py
# you need to set up a Django environnement to use the Class defined in
# the Django models. It is necesssary to interact witht the Django database
#------------------------------------------------------------------------------
# to get the projet.settings it is necessary to add the parent directory
# to the python path
try:
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
except NameError:
    sys.path.append(os.path.abspath('..'))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "projet.settings.settings")
import django
django.setup()

from app2_machine_learning.models import Image, Config

data = sys.argv[1]

def insert_img(data):
    c = Config.objects.get(dataset=data)
    source_path = os.path.join(settings.MEDIA_ROOT,"training",data)
    files = glob.glob(source_path+"/*.jpg")
    for f in files :
        n = os.path.basename(f)
        query = Image(config = c, name = n , process = 0)
        query.save()
    return True, c

if __name__ == '__main__':
    r, c = insert_img(data)
    if r:
        c.valid = True
        c.save()