# -*- coding: utf-8 -*-
"""
Created on Sat May 23 12:58:09 2020

@author: julien
"""
import os
import time
from django.db.models import Count
from app1_base.models import Result, Client, Profile, Object
import json
from django.conf import settings
import glob
from django.core.serializers.json import DjangoJSONEncoder
from shutil import copyfile


# queryset = Object.objects.filter(result_object="car").values('result').annotate(car_nb=Count('result_object'))

# queryset = Result.objects.filter(object__result_object__contains="car").annotate(c=Count('object__result_object'))

# Almost certain images nb same and day
# add negative
def certain(obj):
    queryset = Result.objects.filter(object__result_object__contains=obj).annotate(c=Count('object__result_object'))
    q = queryset.all()
    for r in queryset.all():
        nb_brut = len([i[0] for i in json.loads(r.brut.replace("'", '"')) if i[0] == obj])
        nb_filtered = r.c
        if nb_brut != nb_filtered:
            q = q.exclude(id=r.id).all()
    return q


def write_file(obj):
    q = certain(obj)
    path = '../training/'+obj+'/'
    files = [f for f in glob.glob(path + obj + "*.jpg", recursive=True)]
    for f in files:
        os.remove(f)
    list_result = []
    for r in q:
        list_result += list(Object.objects.filter(result=r, result_object=obj).values(
                'result__camera__client',
                'id',
                'result_id',
                'result_object',
                'result_prob',
                'result_loc1',
                'result_loc2',
                'result_loc3',
                'result_loc4',
                ))
        copyfile(os.path.join(
            settings.MEDIA_ROOT, r.file.split('.')[0]+'_no_box.jpg'), path+str(
            r.camera.client.id)+'_'+obj+str(r.id)+'.jpg')
    with open(path+obj+'.json', 'w', encoding='utf-8') as f:
        json.dump(list_result, f, ensure_ascii=False, indent=4, cls=DjangoJSONEncoder)
    # json.dump(list_result,  cls=DjangoJSONEncoder)

# Almost certain night

# correcting image : missing object with thresh > 0.5

# checking image : missing image with low thresh
