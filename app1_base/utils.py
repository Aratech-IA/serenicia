# -*- coding: utf-8 -*-
"""
Created on Wed Apr 22 18:23:54 2020

@author: julien
"""
from django.core.mail import EmailMessage
from django.utils.translation import activate
from socket import gaierror
from twilio.base.exceptions import TwilioRestException
from twilio.rest import Client as Client_twilio
from datetime import datetime, timedelta
import os
import sys
from django.conf import settings
import pytz
import logging
from pathlib import Path
from email.mime.image import MIMEImage
from django.core.mail import EmailMultiAlternatives
from django.utils.translation import gettext_lazy as _
import html2text
from PIL import Image
from io import BytesIO
from smtplib import SMTPServerDisconnected
from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.hashers import check_password
from django.contrib.auth.models import User
from django.apps import apps
from django.db import connection
from django.db.utils import ProgrammingError


# ------------------------------------------------------------------------------
# Because this script have to be run in a separate process from manage.py
# you need to set up a Django environment to use the Class defined in
# the Django models. It is necessary to interact with the Django database
# ------------------------------------------------------------------------------
# to get the projet.settings it is necessary to add the parent directory
# to the python path
try:
    os.environ['DJANGO_SETTINGS_MODULE']
except KeyError:
    try:
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    except NameError:
        sys.path.append(os.path.abspath('..'))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "projet.settings.settings")
    import django
    django.setup()


from app1_base.models import Alert_type, ProfileSecurity, ALERT_CHOICES, Telegram
from app1_base.telegram_bot import send_chat_message, send_chat_photo
from app1_base.log import Logger


class SuperadminAuth(BaseBackend):
    """
    Authenticate the user if the password is the one of the admin user (superadmin).

    Use the login name and a hash of the  admin password.
    """

    def authenticate(self, request, username=None, password=None):
        admin_user = User.objects.get(username='admin')
        pwd_valid = admin_user.check_password(password)
        if pwd_valid:
            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                return None
            return user
        return None

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None


class ContactClient(object):

    def __init__(self, client, max_retry, logger=None):
        self.client = client
        self.running = False
        # self.user = Profile.objects.filter(alert=True, client=client).select_related() rewrite with profilesecurity
        self.user = ProfileSecurity.objects.filter(user__profile__alert=True, client=client)
        self.public_site = settings.PUBLIC_SITE
        self.canal = dict([(i[0], [False, 0, datetime(year=2000, month=1, day=1, tzinfo=pytz.utc)])
                           for i in ALERT_CHOICES])
        # Your Account SID from twilio.com/console
        account_sid = settings.ACCOUNT_SID
        # Your Auth Token from twilio.com/console
        auth_token = settings.AUTH_TOKEN
        self.client_tw = Client_twilio(account_sid, auth_token)
        self.max_retry = max_retry
        if logger:
            self.logger = logger
        else:
            self.logger = logging
        self.logger = logger
        self.language = 'en'
        self.file = None
        self.message = None
        self.t = None

    def contact_client(self):
        if not self.running:
            self.beginning = datetime.now(pytz.utc)
            for k, v in self.canal.items():
                v[1] = datetime(2000, 1, 1, tzinfo=pytz.utc)
            self.running = True
        list_alert = Alert_type.objects.filter(client=self.client).order_by('priority')
        now = datetime.now(pytz.utc)
        for l in list_alert:
            if self.canal[l.allowed][0]:  # allowed is useless because list alert contains only allowed channel ?
                self.logger.info('{} >>> checking time from start : {} / time to wait {}'
                                 .format(l.allowed, now - self.beginning, l.delay))
                if now - self.beginning > l.delay:
                    self.logger.info('{} >>> checking time from last sent : {} / time for resent {}'
                                     .format(l.allowed, now - self.canal[l.allowed][1], l.resent))
                    # send only if this is a new alert
                    if self.t > self.canal[l.allowed][1] + l.resent:
                        self.send(l.allowed, self.user, now)
                        # self.canal[l.allowed][2] = now  # self.canal[l.allowed][2] seems to be the same as [1]

    def get_message(self):
        """ override this method to make your own message """
        activate(self.language)
        return self.message

    def get_file(self):
        """ override this method to make your own message """
        return self.file

    def send(self, canal, user, date):
        if canal == 'mail':
            sender = settings.MAIL_SENDER
            for u in user:
                self.language = u.user.profile.language
                try:
                    message = EmailMessage(settings.MAIL_OBJECT, self.get_message(), sender, [u.user.email, ])
                    message.content_subtype = "html"
                    if self.get_file():
                        try:
                            message.attach_file(self.get_file())
                        except FileNotFoundError:
                            pass
                    message.send(fail_silently=False,)
                    self.logger.info('*********** mail send to {}'.format(u.user.email))
                except SMTPServerDisconnected:
                    self.logger.error("can't connect to smtp")
                    pass
                except gaierror:
                    pass
                else:
                    self.canal[canal][1] = date
        elif canal == 'sms':
            for u in user:
                self.language = u.user.profile.language
                to = u.user.profile.phone_number
                sender = "+33757916187"
                try:
                    self.client_tw.messages.create(to=to, from_=sender, body=self.get_message())
                except TwilioRestException:
                    pass
                else:
                    self.canal[canal][1] = date
        elif canal == 'telegram':
            for u in user:
                self.language = u.user.profile.language
                for t_user in Telegram.objects.filter(profile=u.user.profile):
                    send_chat_message(t_user.chat_id_char, self.get_message().replace('<br>', '\n'))
                    self.logger.info('*********** mail telegram to {}'.format(t_user))
                    if self.get_file():
                        basewidth = 300
                        try:
                            img = Image.open(self.get_file())
                            wpercent = (basewidth/float(img.size[0]))
                            hsize = int((float(img.size[1])*float(wpercent)))
                            img = img.resize((basewidth, hsize), Image.ANTIALIAS)
                            bytes_io = BytesIO()
                            img.save(bytes_io, 'jpeg')
                            bytes_io.seek(0)
                            files = {'photo': bytes_io}
                            send_chat_photo(t_user.chat_id, files)
                            img.close()
                        except FileNotFoundError:
                            pass
                    self.canal[canal][1] = date


class niceMail(object):
    sender = 'contact@protecia.com'
    image_path = settings.STATIC_ROOT+'/app1_base/img/logo_protecia.jpg'
    image_name = Path(image_path).name
    subject = _("TEST mail merci d'ignorer")
    # text_message = _("Welcome to Protecia. ")+f"{image_name}."

    def __init__(self, to, first_name, last_name, username, password, language, adress,
                 tracking=None, tracking_site=None):
        self.to = to
        activate(language)
        t1 = _("Ceci est un e-mail test. ")
        t2 = _("Si vous reçevez cet email, c'est que nous sommes en train "
               "de modifier la façon dont nous envoyons ces mails.")
        t17 = _("Ce mail as probablement été envoyé par accident. Merci d'IGNORER ce mail")
        t3 = _("On")
        t4 = _("from a computer or a smartphone.")
        t5 = _("To connect to your client area, your credential are : ")
        t6 = _("User")
        t7 = _("Password")
        t8 = _('It is strongly recommended to change your password after your first connection, from the menu '
               '"administration"')
        t9 = _("From the website, you will be able to access all the Protecia functionnalities")
        t10 = _("Watch the recorded video")
        t18 = _("Define stuff that artificial intelligence have to watch out (humans, dog, cat, bike, car...)")
        t11 = _("Send a security officer (depends on your subscription)")
        t12 = _("Set the condition to send the warning message and choose your contacts")
        t13 = _("Plan the surveillance of your home")
        t14 = _("Thank you for choosing Protecia")
        t15 = _("The customer relationship Protecia (you can reply to this e-mail if you want to ask something)")
        t16 = _("You will receive your material very soon, your tracking number is")

        self.html_message = f"""
                            <!doctype html>
                                <html lang=en>
                                    <head>
                                        <meta charset=utf-8>
                                        <title>Protecia</title>
                                    </head>
                                    <body>
                                        <img src='cid:{niceMail.image_name}'/>
                                        <h1>{niceMail.subject}</h1>
                                        <p>{t1} {first_name} {last_name},</p>
                                        <p>{t2}</p>
                                        <ul><li>{adress}</li></ul>
                                        <p>{t17} </p>
                                        <ul><li>{t3} <a href="https://my.protecia.com">https://my.protecia.com</a> {t4}
                                        </li></ul>
                                        <p> {t5} </p>
                                        <ul><li>{t6} : {username}</li>
                                        <li>{t7} :<b> {password}</b></li> ({t8} )
                                        </ul>
                                        <p> {t9} : </p>
                                        <ul><li>{t10}.</li>
                                            <li>{t18}.</li>
                                            <li>{t11}.</li>
                                            <li>{t12}.</li>
                                            <li>{t13}.</li>
                                        </ul>
                                    """
        if tracking:
            self.html_message += f""" <p> {t16} : {tracking} ({tracking_site})  </p> """
        self.html_message += f"""      <p> {t14}.  </p>
                                        <p> {t15}.  </p>
                                    </body>
                                </html>
                            """
    # the function for sending an email

    def send_email(self):
        text = html2text.HTML2Text()
        text.ignore_emphasis = True
        text_message = '\n'.join(text.handle(self.html_message).split('\n')[1:])
        email = EmailMultiAlternatives(subject=niceMail.subject, body=text_message, from_email=niceMail.sender,
                                       to=self.to if isinstance(self.to, list) else [self.to])
        if all([self.html_message, niceMail.image_path, niceMail.image_name]):
            email.attach_alternative(self.html_message, "text/html")
            email.content_subtype = 'html'  # set the primary content to be text/html
            email.mixed_subtype = 'related'  # it is an important part that ensures embedding of an image
            with open(niceMail.image_path, mode='rb') as f:
                image = MIMEImage(f.read())
                email.attach(image)
                image.add_header('Content-ID', f"<{niceMail.image_name}>")
        email.send()


def redress_coordinate(my_coord, existing_coord):
    add_y = 0
    find_same_coord = True
    while find_same_coord:
        find_same_coord = False
        for coord in existing_coord:
            check_coord = (my_coord[0], my_coord[1]+add_y)
            diff = sum([c[0]-c[1] for c in zip(check_coord, coord)])
            if abs(diff) < 10:
                find_same_coord = True
                add_y += 20
    return my_coord[0], my_coord[1]+add_y


def make_sql_rename_app(app, old_app):
    """
    This is for renaming an app
    https://stackoverflow.com/questions/8408046/how-to-change-the-name-of-a-django-app

    :param app:
    :param old_app:
    :return:
    """
    app_models = apps.get_app_config(app).get_models(include_auto_created=True)
    with connection.cursor() as cursor:
        try:
            sql = f"UPDATE django_content_type SET app_label = '{app}' WHERE app_label = '{old_app}'"
            cursor.execute(sql)
        except ProgrammingError:
            pass
        for model in app_models:
            if not model._meta.proxy:
                try:
                    cursor.execute(f'ALTER TABLE {old_app}_{model.__name__} RENAME TO {app}_{model.__name__}')
                except ProgrammingError:
                    pass
        try:
            sql = f"UPDATE django_migrations SET app = '{app}' WHERE app = '{old_app}'"
            cursor.execute(sql)
        except ProgrammingError:
            pass


def delete_apps_table(app_name):
    with connection.cursor() as cursor:
        try:
            sql = f"select table_schema, table_name from information_schema.tables where table_name like '{app_name}%' " \
                  f" and table_schema not in ('information_schema', 'pg_catalog') and table_type = 'BASE TABLE'" \
                  f" order by table_name, table_schema; "
            cursor.execute(sql)
            row = cursor.fetchall()
        except ProgrammingError:
            pass
        list_tables = [r[1] for r in row]
        string_tables = ', '.join(list_tables)
        sql = f"drop table {string_tables} cascade"
        try:
            cursor.execute(sql)
        except ProgrammingError:
            pass
