import os
import sys
import logging

# Because this script has to be run in a separate process from manage.py
# you need to set up a Django environnement to use the Class defined in
# the Django models. It is necessary to interact with the Django database
# ------------------------------------------------------------------------------
# to get the projet.settings it is necessary to add the parent directory
# to the python path
from datetime import datetime

try:
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
except NameError:
    sys.path.append(os.path.abspath('../..'))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "projet.settings.settings")

import django
django.setup()

from django.utils import timezone
from app3_messaging.models import *
from app1_base.log import Logger

# from conv.participants to conv.latest_activity
# from intraemail.copie_c.intermediatecc to intraemail.intermediate
# from intraemail.sender to intraemail.intermediate
# set latest_activity field to true latest activity

# all_msgs = IntraEmail.objects.all()
if 'log_move_data_msg' not in globals():
    global log_mailbox
    log_script = Logger('log_move_data_msg', level=logging.ERROR).run()
log_script.info(f"This script is obsolete, but it's content kept in case of a bug.")
# for msg in all_msgs:
#     log_script.debug(f"msg")
#     try:
#         for intercc in msg.recipients_copie_c.intermediatecc_set.all():
#             log_script.debug(f"msg>for")
#             new_inter, status = Intermediate.objects.get_or_create(recipient=intercc.recipient, message=msg,
#                                                                    date_opened=intercc.date_opened, user_type='CC')
#             new_inter.save()
#
#     except AttributeError:
#         pass
#     if msg.sender:
#         sender = User.objects.get(username=msg.sender)
#         new_sender, status = Intermediate.objects.get_or_create(recipient=sender, message=msg, user_type='sender')
#         new_sender.save()
#
#
# log_script.debug(f"intraemail_length should be equal to inter_sender_length")
# log_script.debug(f"inter_sender_length and inter_cc_length should not increase with further execution of this script.")
# log_script.debug(f"intraemail_length: {len(IntraEmail.objects.all())}")
# log_script.debug(f"inter_sender_length: {len(Intermediate.objects.filter(user_type='sender'))}")
# log_script.debug(f"inter_cc_length: {len(Intermediate.objects.filter(user_type='CC'))}")
