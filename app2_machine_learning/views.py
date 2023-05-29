# -*- coding: utf-8 -*-
"""
Created on Sun Apr 14 21:29:53 2019

@author: julien
"""
import os
import glob
from subprocess import Popen
from django.conf import settings
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, permission_required
from .models import Image, Config
import datetime
import json
import time
# Create your views here.
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseNotFound


def index(request):
    if not request.user.is_authenticated or not request.user.has_perm('app1_base.dataset'):
        return redirect('%s?next=%s' % (settings.LOGIN_URL, request.path))
    directories = os.listdir(os.path.join(settings.MEDIA_ROOT,"training"))
    directories = [ d for d in directories if d !="change_right.sh"]
    return render(request, 'app2_machine_learning/index.html',{'list_dataset':directories})

@login_required
@permission_required('app1_base.dataset')
def dataset(request,dataset):
    config = Config.objects.filter(dataset=dataset)
    if len(config)==0:
        source_path = os.path.join(settings.MEDIA_ROOT,"training",dataset)
        files = glob.glob(source_path+"/*.jpg")
        if len(files)==0:
            return HttpResponseNotFound('<h1>No Page Here</h1>')
        query = Config(dataset=dataset, size = len(files))
        query.save()
        Popen([settings.PYTHON,os.path.join(settings.BASE_DIR,'app2_machine_learning/process_dataset.py'), dataset])
        time.sleep(2)
        progress = len(Image.objects.all())/len(files)
        return HttpResponse('load images in progress : '+ str(progress*100)+'% - please refresh page')   
    elif not config[0].valid:
        progress = len(Image.objects.all())/config[0].size
        return HttpResponse('load images in progress : '+ str(progress)+'%')
    else:
        if settings.DATASET_TEST :
            img = Image.objects.filter(config=config[0])[:100]
        else :  
            img = Image.objects.filter(config=config[0], process=0)[:20]
        list_img = [i.name for i in img]
    return render(request, 'app2_machine_learning/dataset.html',{'list_img':list_img, 'list_dataset':dataset})
    

@login_required
@permission_required('app1_base.dataset')
def img(request, dataset, img_name):
    if request.method == 'POST':
        bb = request.POST.get("box")
        file = request.POST.get("file")
        box = json.loads(bb)
        with open(file, 'w') as f:
            for b in box :
                line = str(b[0])+" "+str(b[1])+" "+str(b[2])+" "+str(b[3])+" "+str(b[4])
                f.write(line+"\n")
        img = Image.objects.get(name=(img_name))
        img.process = 1
        img.time = datetime.datetime.now()
        img.user = request.user
        img.save()
        return HttpResponseRedirect('/train/dataset/'+dataset)
        #return HttpResponse(bb)
        
    try :
        conf = Config.objects.get(dataset=dataset)
        classes = conf.name.split(',')
        ratio = conf.ratio
    except :
        return HttpResponse("no config in the admin")
    
    img = Image.objects.get(name=(img_name))
    file = os.path.join(settings.MEDIA_ROOT,"training",dataset,img.name.split('.')[0]+'.txt')
    
    
    
    bb = []
    try :
        with open(file, 'r') as f:
            content = f.readlines()
            for line in content:
                values_str = line.split()
                class_index, x_center, y_center, x_width, y_height = map(float, values_str)
                class_index = int(class_index)
                bb.append([class_index, x_center, y_center, x_width, y_height])
    except FileNotFoundError : 
        pass
        
    context = {'img' : "/media/training/"+dataset+"/"+img.name, 'ratio' : ratio,
               'classes' : classes, 'file' : file, 'bb' : bb, 'dataset' : dataset, 'img_name' : img.name  }
    return render(request, 'app2_machine_learning/img.html',context)

