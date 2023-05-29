from email.parser import Parser
import email
import poplib
import getpass
import imaplib
import logging
import re
import os
import sys
import datetime

try:
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
except NameError:
    sys.path.append(os.path.abspath('../..'))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "projet.settings.settings")

import django
django.setup()

from django.contrib.auth.models import User
from app1_base.log import Logger
from django.conf import settings

# pip install imap_tools
email_adress = settings.MASS_MAILLING_EMAIL
password = settings.MASS_MAILLING_PASSWORD
server_name = settings.MASS_MAILLING_SERVER
port = settings.MASS_MAILLING_PORT

if 'log_get_mails' not in globals():
    global log_get_mails
    log_get_mails = Logger('read_mails', level=logging.ERROR, file=False).run()
mail = imaplib.IMAP4(host=server_name)
mail.login(email_adress, password)
mail.select()
# type_mail, data = mail.search(None, 'FROM', '"MAILER-DAEMON"')
type_mail, data = mail.search(None, '(FROM "MAILER-DAEMON" UNSEEN)')
mail_ids = data[0].decode('utf-8')
id_list = mail_ids.split()
# log_get_mails.debug(mail.list())
log_get_mails.debug(f"----------------------------------INBOX--------------------------------")
mail.select('INBOX', readonly=True)
id_list.reverse()
for i in id_list:
    typ, msg_data = mail.fetch(str(i), '(RFC822)')
    for response_part in msg_data:
        if isinstance(response_part, tuple):
            msg = email.message_from_bytes(response_part[1], policy=email.policy.default)
            log_get_mails.debug(msg['from']+"\t"+msg['subject']+"\t"+msg['date'])
            body = msg.get_body(preferencelist=('plain', 'html', 'related'))
            try:
                text = body.get_content()
            except LookupError:
                break
            pattern = re.compile(r'[\w.+-]+@[\w-]+\.[\w.-]+')
            try:
                # log_get_mails.debug(re.search(pattern, text))
                finds = re.search(pattern, text).group(0)
                # log_get_mails.debug(finds)
                try:
                    users = User.objects.filter(email=finds)
                    for user in users:
                        profile = user.profile
                        if not profile.mailer_daemon:
                            profile.mailer_daemon = True
                            profile.save()
                            # log_get_mails.debug(f"---{finds}, {user}, {profile.mailer_daemon}")
                        else:
                            pass
                            # log_get_mails.debug(f"{user} should already be exempt")
                        try:
                            profile.preferences.notif_all_new_msg = False
                            profile.preferencesserenicia.notif_family_new_picture = False
                            profile.preferencesserenicia.notif_doctor_demand_date = False
                            profile.preferencesserenicia.sensitive_photos = False
                            profile.preferencesserenicia.interventions = False
                            profile.preferences.save()
                            profile.preferencesserenicia.save()
                        except AttributeError:
                            pass
                        profile.save()
                except User.DoesNotExist:
                    log_get_mails.debug(f"{finds} DOES NOT EXIST")
            except AttributeError:
                log_get_mails.debug(f"EMAIL ADRESS NOT FOUND OR INVALID")
                # log_get_mails.debug(f"{text}")
for i in id_list:
    mail.store(i, '+FLAGS', '\\Seen')
mail.close()
mail.logout()
