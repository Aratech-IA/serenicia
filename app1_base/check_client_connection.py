# -*- coding: utf-8 -*-
"""
Created on Wed Mar 11 14:39:29 2020

@author: julien
"""
import logging
import os
import sys
from django.conf import settings
import time
import pytz
from log import Logger
from datetime import datetime
from django.utils.translation import gettext as _
from django.utils.translation import activate
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

from app1_base.models import Client
from app1_base.utils import ContactClient


class myContactClient(ContactClient):
    def get_message(self):
        activate(self.language)
        message = _("{} {}, your cameras at {} are no more connected until {:%d-%m-%Y - %H:%M:%S} \
                    because of power or internet outage at your home").format(
                                self.client.first_name, self.client.name, self.client.city, self.t)
        return message


class reconnectClient(ContactClient):
    def get_message(self):
        activate(self.language)
        message = _("{} {}, your cameras at {} are now connected until {:%d-%m-%Y - %H:%M:%S}").format(
                                self.client.first_name, self.client.name, self.client.city, self.t)
        return message  
        

class processConnection(object):

    def __init__(self):
        self.warn_client = {}
        self.reconnect_client = {}

    def run(self, period):
        while True:
            for client in Client.objects.filter(actif=True, ping=True):
                time_gap = datetime.now(pytz.utc)-client.timestamp
                time_from_last_connection = time_gap.seconds
                if time_from_last_connection > 500:
                    logger.warning('Client {} is not connected for {} seconds '.format(client.name,
                                                                                       time_from_last_connection))
                    try:
                        self.warn_client[client.id]
                    except KeyError:
                        self.warn_client[client.id] = myContactClient(client, 3, logger)
                        self.warn_client[client.id].t = client.timestamp.astimezone(pytz.timezone(client.time_zone))
                        self.warn_client[client.id].canal['mail'][0] = True
                        self.warn_client[client.id].canal['telegram'][0] = True
                        pass
                    self.warn_client[client.id].contact_client()
                    client.video_authorize = False
                    client.save(update_fields=['connected', ])
                else:
                    client.video_authorize = True
                    client.save(update_fields=['connected', ])
                    logger.info('client {} connected'.format(client))
                    try:
                        del(self.warn_client[client.id])
                        self.reconnect_client[client.id] = reconnectClient(client, 1, logger)
                        self.reconnect_client[client.id].t = client.timestamp.astimezone(pytz.timezone(
                            client.time_zone))
                        self.reconnect_client[client.id].canal['mail'][0] = True
                        self.reconnect_client[client.id].canal['telegram'][0] = True
                        self.reconnect_client[client.id].contact_client()       
                    except KeyError:
                        pass
            time.sleep(period)

# start the process


if __name__ == '__main__':
    ####### log #######
    if settings.DEBUG:
        level = logging.DEBUG
    else:
        level = logging.WARNING
    logger = Logger('connection', level).run()
    ####################
    p = processConnection()
    p.run(30)
