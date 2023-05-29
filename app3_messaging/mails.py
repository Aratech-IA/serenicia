import sys
import os
import random
import logging

from smtplib import SMTPDataError, SMTPConnectError, SMTPServerDisconnected
from typing import List
from app1_base.log import Logger
from django.template.loader import render_to_string
from django.template import Context, Template
from django.conf import settings
import django.core.mail as djm
from app1_base.models import User
import app3_messaging.textprocess as textprocess
from app3_messaging.models import DataEmail, Campaign, CreateEmail


def send_mass_html_mail(args, fail_silently=False, user=None, password=None,
                        connection=None):
    """
    Given a datatuple of (subject, text_content, html_content, from_email,
    recipient_list), sends each message to each recipient list. Returns the
    number of emails sent.

    If from_email is None, the DEFAULT_FROM_EMAIL setting is used.
    If auth_user and auth_password are set, they're used to log in.
    If auth_user is None, the EMAIL_HOST_USER setting is used.
    If auth_password is None, the EMAIL_HOST_PASSWORD setting is used.

    """
    connection = connection or djm.get_connection(
        username=user, password=password, fail_silently=fail_silently)
    messages = []
    subject, text, html, from_email, recipient = args
    for r in recipient:
        message = djm.EmailMultiAlternatives(subject, text, from_email, [r, ])
        message.attach_alternative(html, 'text/html')
        messages.append(message)
    return connection.send_messages(messages)


def sendnotif(subject: str, templatename: str, recipient_emails: List[str], flexcontent: List[str],
              link_redirect: List[str], nomsymbdjango: List[str], sender: str, files: List[str] = False,
              debugsymbdjango: bool = False, symbflexnames: bool = True, fail_silently: bool = False, user=None,
              password=None, connection=None):
    """
    :param subject: Subject of mail
    :param templatename: is the name of the template, must be in app3_messaging/templates/app3_messaging/notiftemplates/
    :param recipient_emails: list of the recipient's emails, cannot be empty
    :param flexcontent: [THE ELEMENTS OF THE LIST MUST BE STRINGS OR ABLE TO BE CONVERTED INTO STRINGS VIA THE str()
                    METHOD. ]
                    NOTE: The order of the list is IMPORTANT. the list is run through and "¤" symbols in the template
                    are replaced by the elements in the list. Example: if list has ["marc", "lucie"] then first
                    iteration of "¤" is replaced by marc and the second one by lucie
    :param link_redirect: Lien pour un bouton de redirection. Si vide, le lien sera cassé...
    :param nomsymbdjango: name of django's var (in french) used in the email
                    ex: nom = user.last_name while prénom = user.first_name
                    NOTE: must be in order of apparition, the same as flexcontent
                    NOTE: accepted values can be seen (and added) within the possivardjango() def in textprocess.py
                    of app3_messaging.
    :param sender: email adress of sender. May not be the adress of a registered User
    :param files: List of file paths
    :param debugsymbdjango: Un booléen, valant par défaut False. Si True, les nom de variables django qui n'ont
                    pas de contreparties seront mis avec un message de debug
    :param symbflexnames: Mettre vrai si la template as des ¤variables¤ dedans
    :param fail_silently: paramètres pour l'envoi de mail
    :param user: paramètres pour l'envoi de mail
    :param password: paramètres pour l'envoi de mail
    :param connection: paramètres pour l'envoi de mail

    """
    if 'log_mails' not in globals():
        global log_mails
        log_mails = Logger('mails_notif', level=logging.ERROR, file=True).run()
    recipient_emails = [x for x in recipient_emails if len(x.strip()) > 0]  # remove if email empty
    log_mails.debug(f"step 1 {recipient_emails}")
    domain = settings.PUBLIC_SITE
    log_mails.debug(f"step 2 {domain}")
    connection = connection or djm.get_connection(
        username=user, password=password, fail_silently=fail_silently)
    log_mails.debug(f"step 3 {connection}")
    messages = []
    rawcontent = "app3_messaging/notiftemplates/" + templatename + ".html"
    log_mails.debug(f"step 4 {rawcontent}")
    rawcontent = render_to_string(rawcontent)
    log_mails.debug(f"step 5")
    rawcontent = rawcontent.replace("[[ domain ]]", domain)
    rawcontent = textprocess.creation_lien_mail_redirect(rawcontent, link_redirect)
    log_mails.debug(f"step 6 {link_redirect}")
    if debugsymbdjango:
        rawcontent = textprocess.replacevardjango(nomsymbdjango, rawcontent, True)
    else:
        rawcontent = textprocess.replacevardjango(nomsymbdjango, rawcontent)
    log_mails.debug(f"step 7 {nomsymbdjango}")
    if symbflexnames:
        flexcontent = textprocess.linereturnbr(flexcontent)
        rawcontent = textprocess.removename(rawcontent, flexcontent)
    log_mails.debug(f"step 8 {flexcontent}")
    itera = 0

    for r in recipient_emails:
        content = rawcontent
        clef = textprocess.idcreate(itera)
        date = textprocess.get_date()
        log_mails.debug(f"step 9-1 {r}")
        context, user = textprocess.create_context_get_user(r, clef)
        log_mails.debug(f"step 9-2 {context}")
        content = textprocess.creationlien(content, clef)
        t = Template(content)
        log_mails.debug(f"step 9-3 {user}")
        content = t.render(Context(context))
        log_mails.debug(f"step 9-4")
        plaintext = textprocess.htmltotext(content)
        log_mails.debug(f"step 9-5")
        add_to_log = DataEmail(clef=clef, user=user, email_adress_sender=sender, subject=subject,
                               content=content, date_creation=date, date_sent=date, is_notif=True)
        log_mails.debug(f"step 9-6 {add_to_log.user}")
        add_to_log.save()
        log_mails.debug(f"step 9-7")
        message = djm.EmailMultiAlternatives(subject, plaintext, sender, [r, ])
        log_mails.debug(f"step 9-8")
        message.attach_alternative(content, 'text/html')
        if files:
            for path in files:
                message.attach_file(path)
        log_mails.debug(f"step 9-9")
        messages.append(message)
        itera += 1
    if not settings.DEBUG or settings.SEND_MAIL:
        try:
            envoi = connection.send_messages(messages)
            log_mails.debug(f"step 9-10 if 0 then not sent: {envoi}")
        except (SMTPServerDisconnected, SMTPDataError):
            envoi = 0
            log_mails.debug(f"step 9-10 if 0 then not sent: {envoi}")
    else:
        log_mails.debug(f"does not have the correct settings to send mail")

    log_mails.debug(f"\n-------------------------------------------------------------------------\n")


def createcampaign(subject, sender, recipient_emails, key, name="", has_name=False):
    """
        :param subject: Subject of mail
        :param sender: sender mail
        :param recipient_emails: list of the recipient's emails, cannot be empty
        :param key: primary key of the model used.
        :param name: name of campaign.
        :param has_name: True if the campaign need to be named.
    """
    if 'log_mails_notif' not in globals():
        global log_mails_notif
        log_mails_notif = Logger('mails_details', level=logging.ERROR, file=True).run()
    log_mails_notif.debug(f"step 1")
    itera = 0
    maillist = []
    campaign = Campaign()
    log_mails_notif.debug(f"step 2")
    if has_name:
        campaign.nom_de_la_campagne = name
    log_mails_notif.debug(f"step 3")
    campaign.mail_type = key
    log_mails_notif.debug(f"step 4")
    sender_user = User.objects.get(email=sender)
    log_mails_notif.debug(f"step 5")
    campaign.sender = sender_user
    log_mails_notif.debug(f"step 6")
    campaign.save()
    log_mails_notif.debug(f"step 7")
    id_campaign = campaign.pk
    log_mails_notif.debug(f"step 8")
    for r in recipient_emails:
        log_mails_notif.debug(f"step 9-1")
        clef = textprocess.idcreate(itera)
        log_mails_notif.debug(f"step 9-2")
        context, user = textprocess.create_context_get_user(r, clef)
        log_mails_notif.debug(f"step 9-3 {user}")
        add_to_log = DataEmail(
            clef=clef, user=user, email_adress_sender=sender, subject=subject, campaign_of_mail=campaign,
            date_creation=textprocess.get_date())
        log_mails_notif.debug(f"step 9-4 {add_to_log.user}")
        maillist.append(add_to_log)
        log_mails_notif.debug(f"step 9-5")
        add_to_log.save()
        log_mails_notif.debug(f"step 9-6")
        itera += 1
    return maillist, id_campaign


def sendcampaign(maillist, fail_silently=False, user=None, password=None, connection=None):

    """
    :param maillist: list of mails.
    :param fail_silently: paramètres pour l'envoi de mail
    :param user: paramètres pour l'envoi de mail
    :param password: paramètres pour l'envoi de mail
    :param connection: paramètres pour l'envoi de mail
    """

    if 'log_mails' not in globals():
        global log_mails
        log_mails = Logger('mails_details', level=logging.ERROR, file=True).run()
    log_mails.debug(f"send-step 1")
    get_campaign = maillist[0]
    key = get_campaign.campaign_of_mail.mail_type.id
    log_mails.debug(f"send-step 2")
    mail_type = CreateEmail.objects.get(pk=key)
    log_mails.debug(f"send-step 3")
    content = mail_type.content
    log_mails.debug(f"send-step 4")
    connection = connection or djm.get_connection(
        username=user, password=password, fail_silently=fail_silently)
    log_mails.debug(f"send-step 5")
    messages = []
    for mail in maillist:
        if ' ' not in mail.user.email and all(x in mail.user.email for x in ['.', '@']) and mail.user.email != '':
            log_mails.debug(f"send-step 6-1")
            contenttext = textprocess.render_apercu_mail(mail.user.email, mail.clef, content)
            log_mails.debug(f"send-step 6-2")
            contenttext = textprocess.creationlien(contenttext, mail.clef)
            log_mails.debug(f"send-step 6-3")
            campaign = mail.campaign_of_mail
            log_mails.debug(f"send-step 6-4")
            sender_user = User.objects.get(email=mail.email_adress_sender)
            log_mails.debug(f"send-step 6-5")
            campaign.sender = sender_user  # update already created campaigns
            log_mails.debug(f"send-step 6-6")
            campaign.save()
            log_mails.debug(f"send-step 6-7")
            plaintext = textprocess.htmltotext(contenttext)
            log_mails.debug(f"send-step 6-8")
            message = djm.EmailMultiAlternatives(mail.subject, plaintext, mail.email_adress_sender, [mail.user.email, ])
            log_mails.debug(f"send-step 6-9")
            message.attach_alternative(contenttext, 'text/html')
            messages.append(message)
            if settings.SEND_MAIL:
                log_mails.debug(f"send-step 6-10")
                try:
                    log_mails.debug(f"message : {message.to}")
                    envoi = connection.send_messages([message, ])
                    log_mails.debug(f"ssend mail to {mail.user.email}: {envoi}")
                except (SMTPServerDisconnected, SMTPDataError):
                    envoi = 0
                    log_mails.debug(f"send mail to {mail.user.email}: {envoi}")
                if envoi:
                    mail.date_sent = textprocess.get_date()
                    mail.save()
                    campaign.number_sent += 1
                    campaign.save()
            # log_mails.debug(f"{contenttext}")
            log_mails.debug(f"\n-------------------------------------------------------------------------\n")
        else:
            log_mails.debug(f"skipped unconforming email: {mail.user.email}")
            print(f"skipped unconforming email: {mail.user.email}")
