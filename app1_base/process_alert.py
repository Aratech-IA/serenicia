# -*- coding: utf-8 -*-
"""
Created on Sat Feb  3 11:58:19 2018

@author: julien

Main script to process the camera images
"""
import logging
import os
import sys
import time
from django.conf import settings
from logging.handlers import RotatingFileHandler
from collections import Counter
from django.utils.translation import gettext as _
from django.utils.translation import activate
# from django.db import DatabaseError
from django.db.models import Count
import secrets
import pytz
from datetime import datetime

# ------------------------------------------------------------------------------
# Because this script have to be run in a separate process from manage.py
# you need to set up a Django environnement to use the Class defined in
# the Django models. It is necesssary to interact witht the Django database
# ------------------------------------------------------------------------------
# to get the projet.settings it is necessary to add the parent directory
# to the python path
try:
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
except NameError:
    sys.path.append(os.path.abspath('..'))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "projet.settings.settings")
import django
django.setup()

from app1_base.models import Profile, Result, Object, Alert, Camera, Client, DISAPPEAR
from app1_base.utils import ContactClient

    
class MyContactClient(ContactClient):

    def get_message(self):
        activate(self.language)
        body = _("Origin of detection") + " : {}".format(
            self.alert.stuffs_char_foreign.stuffs)+"   ---  "+_(
            "Type of detection")+":  {}".format(self.alert.actions_char)
        body += "<br>"+_("Time of detection")+": {:%d-%m-%Y - %H:%M:%S}".format(self.t)
        body += "<br>"+_("Please check the images")+": {} ".format(settings.PUBLIC_SITE+'/warning/0/'+self.alert.key)
        return body


class ProcessAlert(object):
    def __init__(self, key):
        self.client = Client.objects.get(key=key)
        ####### log #######
        if settings.DEBUG:
            level = logging.DEBUG
        else:
            level = logging.WARNING
        self.logger = logging.getLogger(str(self.client.id))
        self.logger.setLevel(level)
        formatter = logging.Formatter('%(asctime)s:: %(levelname)s:: %(message)s')
        file_handler = RotatingFileHandler(
            os.path.join(settings.BASE_DIR, 'log', 'alert'+str(self.client.id)+'.log'), 'a', 10000000, 1)
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)
        ####################
        # self.user = Profile.objects.filter(alert=True, client=self.client).select_related()
        self.public_site = settings.PUBLIC_SITE
        self.running = True
        self.warn = {}
        alert = Alert.objects.filter(active=True, client=self.client)
        for a in alert:
            a.active = False
            a.save()
        # case where present alert is on at the launch
        self.cam = Camera.objects.filter(active=True, client=self.client)
        self.dict_obj = {}
        self.counter_obj = {}

    def check_alert(self, result, alert_type, object_counter):
        for s in object_counter:
            a = Alert.objects.filter(stuffs_char_foreign__stuffs=s,
                                     actions_char=alert_type,
                                     camera=result.camera,
                                     client=self.client).first()
            if a:
                self.logger.info(alert_type+' alert: {}'.format(a))
                result.alert = True
                result.save()
                a.img_name = result.file
                a.last = result.time
                a.save()
                if not a.active:
                    a.active = True
                    a.key = secrets.token_urlsafe(6)
                    a.when = result.time
                    a.save()

    # def obj_to_list(self, obj):
    #     list_object = []
    #     for o in obj:
    #         list_object.append([o.result_object, (
    #             float(o.result_loc1), float(o.result_loc2), float(o.result_loc3), float(o.result_loc3)), 0, 0])
    #     return list_object
    #
    # def diff_pos(self, pos1, pos2):
    #     return (sum([abs(i-j) for i, j in zip(pos1, pos2)]))/(pos1[2]+pos1[3])*100

    def run(self, _time):
        # just wait to collect image for start point
        time.sleep(self.client.wait_before_detection)
        # start point for obj on each cam
        for c in self.cam:
            result = Result.objects.filter(camera=c).last()
            o = Object.objects.filter(result=result)
            c_obj = Counter([i.result_object for i in o])
            self.check_alert(result, 'present', c_obj)
            # self.dict_obj[c.id] = self.obj_to_list(o)
            self.counter_obj[c.id] = [Counter([i.result_object for i in o]), {}]  # c.nb_obj = {}  better ?
        self.logger.info('getting last object init: {}'.format(self.dict_obj))
        self.result = Result.objects.filter(camera__client=self.client).last()
        while self.running:
            # Is there new result
            rn = Result.objects.filter(pk__gt=getattr(self.result, 'id', 0),
                                       camera__client=self.client,
                                       force_send=False)
            activate('en')
            for r in rn:
                self.logger.info('new result in databases: {}'.format(r))
                on = Object.objects.filter(result=r)
                cn = Counter([i.result_object for i in on])
                self.logger.debug('getting objects in databases: {}'.format(cn))
                # case "is present"
                self.check_alert(r, 'present', cn)
                # case: "add"
                adding_object = cn - self.counter_obj[r.camera.id][0]
                self.counter_obj[r.camera.id][0] += adding_object
                self.check_alert(r, 'appear', adding_object)
                # case: "suppr"
                suppr_object = self.counter_obj[r.camera.id][0] - cn
                for obj, nb in suppr_object.items():
                    if obj not in DISAPPEAR:
                        self.counter_obj[r.camera.id][0] -= Counter({obj: nb})
                        self.check_alert(r, 'disappear', [obj, ])
                    else:
                        if obj not in self.counter_obj[r.camera.id][1]:
                            self.counter_obj[r.camera.id][1][obj] = [r, 0, Counter({obj: nb})]
                for s in self.counter_obj[r.camera.id][1].copy():
                    if s not in suppr_object:
                        del self.counter_obj[r.camera.id][1][s]
                self.result = r
            # check disappear if no more result, count time
            # only for object in DISAPPEAR
            for c in self.cam:
                for obj, value in self.counter_obj[c.id][1].copy().items():
                    if value[1] < DISAPPEAR[obj]:
                        self.counter_obj[c.id][1][obj][1] += 1
                    else:
                        self.check_alert(value[0], 'disappear', [obj, ])
                        self.counter_obj[c.id][0] -= value[2]
                        del self.counter_obj[c.id][1][obj]

            # This part is for sending the alert to the client
            alert = Alert.objects.filter(client=self.client)
            for a in alert:
                if a.active:
                    #  time from last detection is under the max quiet time
                    if datetime.now(pytz.utc) - a.last < self.client.wait_before_cancel_alert:
                        try:
                            self.warn[a.id]
                        except KeyError:
                            # create contact
                            self.warn[a.id] = MyContactClient(self.client, 1, logger=self.logger)

                            # allowed all channel
                            for k, v in self.warn[a.id].canal.items():
                                v[0] = True
                        self.warn[a.id].t = a.last.astimezone(pytz.timezone(self.client.time_zone))
                        path_im = None
                        for i in range(5):
                            try:
                                path_im = settings.MEDIA_ROOT+'/'+a.img_name
                                img = open(path_im, 'rb')
                                img.close()
                                break
                            except (FileNotFoundError, IOError):
                                time.sleep(2)
                                pass
                        self.warn[a.id].file = path_im
                        self.warn[a.id].alert = a
                        self.warn[a.id].contact_client()
                    else:  # cancel the alert because the place is quiet for sufficient time
                        a.active = False
                        a.save(update_fields=["active"])
                else:
                    try:
                        del(self.warn[a.id])
                    except:
                        pass
            time.sleep(_time)


def main():
    key = sys.argv[1]
    activate('en')
    # instanciate process alert
    process_alert = ProcessAlert(key)
    # print("Waiting...")
    # process_alert.wait()
    print("Alert are running !")
    try:
        process_alert.run(1)
    except KeyboardInterrupt:
        print("Bye bye!")

# start the threads


if __name__ == '__main__':
    main()
