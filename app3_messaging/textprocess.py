import re
import datetime
import asyncio
import urllib

from bs4 import BeautifulSoup
from django.template.loader import render_to_string
from django.template import Context, Template
from django.contrib.auth.models import User
from django.db.models import Q
from django.conf import settings as param
from django.utils import timezone
from app1_base.log import Logger
import logging
from app1_base.models import Client, Profile
from app3_messaging.models import DataEmail, CreateEmail
from django.utils.translation import gettext_lazy as _

logger = Logger('unsent_cleaning', level=logging.ERROR, file=False).run()


def htmltotext(html):
    if 'log_mails' not in globals():
        global log_mails
        log_mails = Logger('mails', level=logging.ERROR, file=True).run()
    """Remove html tags from a string"""

    linereturn = re.compile('\n')
    linereturnhtml = re.compile('<br>')
    linereturn2html = re.compile('<br />')
    cleaninnerstyle = re.compile('<style>.*?</style>')
    cleaninnerstyle2 = re.compile('<title>.*?</title>')
    cleanpreheader = re.compile("<span class=.preheader.(.|\n)*?span>")
    html = re.sub(linereturn, '', html)
    html = re.sub(linereturnhtml, '\n', html)
    html = re.sub(linereturn2html, '\n', html)
    html = re.sub(cleaninnerstyle, '', html)
    html = re.sub(cleaninnerstyle2, '', html)
    html = re.sub(cleanpreheader, '', html)
    html = re.sub(' +', ' ', html)
    soup = BeautifulSoup(html, 'html.parser')
    all_a = soup.findAll('a')
    for m in all_a:
        log_mails.debug(f"{m.string} + ':' + {m['href']}")
        if m.string:
            thing = m.string + " : " + m['href']
            m.previousSibling.replaceWith(m.previousSibling + thing)
            m.extract()
    html = soup.get_text()
    html = re.sub(' +', ' ', html)
    return html


def convert_string(string):
    respace = re.compile(r'[^a-zA-Z0-9-_\n]')
    string = re.sub(respace, '', string)
    return string


def removename(template, flexcontent):
    for flexvar in flexcontent:
        template = re.sub(r"¤\w+¤", str(flexvar), template, 1)
    return template


def create_context_get_user(recipient_email, clef):
    user = User.objects.filter(email=recipient_email)
    user = user[0]
    try:
        profile = Profile.objects.get(user=user)
        if not profile.civility:
            profile_user = ""
        else:
            profile_user = profile
    except Profile.DoesNotExist:
        profile_user = ""
    context = {"user": user, "clef": clef, "profile": profile_user}
    return context, user


def render_apercu_mail(recipient_email, clef, content):
    t = Template(content)
    context, user = create_context_get_user(recipient_email, clef)
    contenttext = t.render(Context(context))
    return contenttext


def possivardjango():
    dicovardjango = {"Last Name": "{{ user.last_name}}", "First Name": "{{ user.first_name }}", "email": "{{ user.email }}",
                     "Groups": "{{ user.groups.all }}", "Username": "{{ user.get_username }}",
                     "Civility": "{{ profile.civility }}"}
    return dicovardjango


def replacevardjango(nomsymbdjango, content, debug=False):
    newsymbdjango = []
    for el in nomsymbdjango:
        if el != "":
            newsymbdjango.append(el)
    dicovardjango = possivardjango()
    for nomvar in newsymbdjango:
        if nomvar in dicovardjango:
            vardjango = dicovardjango[nomvar]
            content = re.sub(r"%%\w+%%", vardjango, content, 1)
        else:
            if debug:
                content = re.sub(r"%%\w+%%", "var_not_found", content, 1)
            else:
                content = re.sub(r"%%\w+%%", "", content, 1)
    return content


def emailrender(templatename, flexcontent, nomsymbdjango, domain, link_redirect):
    """
    :param templatename: name of the template
    :param flexcontent: [THE ELEMENTS OF THE LIST MUST BE STRINGS OR ABLE TO BE CONVERTED INTO STRINGS VIA THE str()
                    METHOD. ]
                    NOTE: The order of the list is IMPORTANT. the list is run through and "¤" symboles in the template
                    are replaced by the elements in the list. Example: if list has ["marc", "lucie"] then first
                    iteration of "¤" is replaced by marc and the second one by lucie
    :param nomsymbdjango: le nom des variables django dans la template mail. Est une liste.
    :param domain: nom du domaine de l'application mail via laquelle ce mail as été envoyé.
    :param link_redirect: liens sur lesquels ont vas rediriger. est une liste
    """
    if 'log_mails' not in globals():
        global log_mails
        log_mails = Logger('mails_details', level=logging.ERROR, file=True).run()
    flexcontent = [x for x in flexcontent if len(x.strip()) > 0]
    nomsymbdjango = [x for x in nomsymbdjango if len(x.strip()) > 0]
    link_redirect = [x for x in link_redirect if len(x.strip()) > 0]
    content = "app3_messaging/emailtemplates/" + templatename + ".html"
    log_mails.debug(f"render-step1")
    content = render_to_string(content)
    log_mails.debug(f"render-step2")
    data = param.STATIC_URL
    log_mails.debug(f"render-step3 STATIC UTL:{data}")
    content = content.replace("[[ domainstatic ]]", data)
    log_mails.debug(f"render-step4 domain: {domain}")
    content = content.replace("[[ domain ]]", domain)
    log_mails.debug(f"render-step5 link_redirect: {link_redirect}")
    content = creation_lien_mail_redirect(content, link_redirect)
    log_mails.debug(f"render-step6 nomsymbdjango: {nomsymbdjango}")
    content = replacevardjango(nomsymbdjango, content)
    log_mails.debug(f"render-step7 flexcontent: {flexcontent}")
    flexcontent = linereturnbr(flexcontent)
    log_mails.debug(f"render-step8")
    content = removename(content, flexcontent)
    return content


def linereturnbr(flexcontent):
    flexcontent = [str(flexvar).replace("\n", "<br>") for flexvar in flexcontent]
    return flexcontent


def idcreate(itera):
    date = get_date()  # recup temps
    datestr = str(date)
    clef = datestr  # créer clef pour creation du lien
    clef += str(itera)  # ajout des derniéres data
    clef = re.sub("[. _:-]", '', clef)  # suppression des charactéres spéciaux
    return clef


def get_date():
    date = timezone.now()
    return date


def cleaning_unsent():
    # does not work with not naive datetime
    date = get_date()
    list_data_email = DataEmail.objects.filter(date_sent__is_null=True)
    for email in list_data_email:
        dateemail = email.date_creation
        try:
            if not email.campaign_of_mail.nom_de_la_campagne:
                if dateemail and (date - dateemail).days > 30:
                    email.delete()
        except AttributeError:
            if dateemail and (date - dateemail).days > 30:
                email.delete()


def creationlien(content, clef):
    string = "/appmail/mails/lien/open/" + clef
    string_unsubscribe = "/appmail/mails/lien/unsubscribe/"+clef
    string_click = "/appmail/mails/lien/click/" + clef
    content = re.sub("#link_click#", string_click, content)
    content = re.sub("#link#", string, content)
    content = re.sub("#link_unsubscribe#", string_unsubscribe, content)
    return content


def creation_lien_mail_redirect(content, link_redirect):
    for link in link_redirect:
        content = re.sub(r"µ\w+µ", link, content, 1)
    return content

# ---------------------------------- UTILS ? ---------------------------


def func_istoobig(listmails, content, lot=None):
    if len(listmails) > 200:
        if lot:
            istoobig = lot
        else:
            istoobig = len(listmails)
        listemail = [render_apercu_mail(listmails[0].user.email, listmails[0].clef, content)]
    else:
        istoobig = False
        listemail = []
        for mail in listmails:
            dicosaid_campaign = {"NAME": mail,
                                 "LIST": render_apercu_mail(mail.user.email, mail.clef, content)}
            listemail.append(dicosaid_campaign)
    return istoobig, listemail


def get_recipients(request):
    if 'log_mails' not in globals():
        global log_mails
        log_mails = Logger('mails_details', level=logging.WARN, file=True).run()
    recipients = []
    try:
        recipients = request.POST.getlist("recipients[]")
    except KeyError:
        pass
    try:
        recipientgroup = request.POST.getlist("allprospects[]")
        if recipientgroup:
            temp_user_list = User.objects.filter(Q(groups__name__in=recipientgroup))
            temp_user_list = temp_user_list.exclude(profile__subscribe_emails=False).exclude(is_active=False).exclude(profile__mailer_daemon=True)
            unconform_users = User.objects.filter(Q(groups__name__in=['prospect']),
                                                  ~Q(email__icontains='@') | ~Q(email__icontains='.') | Q(email="") | Q(email__icontains=' '))
            log_mails.warn(f"The following users don't possess conform emails: {unconform_users}")
            for user in temp_user_list:
                recipients.append(user.email)
    except KeyError:
        pass
    return recipients


def get_info(request):
    data = dict(request.POST.items())
    nomdumailtype = data["templatefilename"]
    createemail = CreateEmail.objects.get(nom_du_mail_type=nomdumailtype)
    key = createemail.id
    recipients = get_recipients(request)
    subject = data["subject"]
    return data, createemail, key, recipients, subject
