import glob
import re
import time
import asyncio
import logging

from urllib.parse import urlparse
from asgiref.sync import sync_to_async, async_to_sync
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.db.models.functions import Lower
from django.core.paginator import Paginator
from django.template.defaultfilters import lower
from django.urls import reverse
from django.utils import timezone
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.models import Group, User
from django.contrib.auth import login
from django.conf import settings as param

from app3_messaging.utils import get_users
from app3_messaging.tokens import account_activation_token
from app3_messaging.mails import sendcampaign, createcampaign
from app3_messaging.models import DataEmail, CreateEmail, IntraEmail, IntraEmailAttachment, Intermediate, Campaign, \
    Conversation, Notification
from app1_base.models import Profile, ProfileSecurity
from app3_messaging.forms import CreateEmailForm, IntraEmailAttachmentForm, CreateCampaignForm, SignUpForm
import app3_messaging.textprocess as textprocess
from app1_base.log import Logger


# The model used for this app depend on the domain Protecia or Serenicia, we need to get the correct model.
if "protecia" in param.DOMAIN.lower():
    model_linked = ProfileSecurity
else:
    from app4_ehpad_base.models import ProfileSerenicia
    model_linked = ProfileSerenicia

#  ---------------------------------------- DEBUT MAILS ----------------------------------------------------------------


@login_required
@permission_required('app0_access.view_communication')
def mails(request):
    try:
        request.session.pop('resident_id')
    except KeyError:
        pass
    if 'log_mails' not in globals():
        global log_mails
        log_mails = Logger('mails', level=logging.ERROR, file=False).run()
    connected_user = ''
    if request.user.is_authenticated:
        connected_user = User.objects.get(pk=request.user.id)
    templateslist = glob.glob("app3_messaging/templates/app3_messaging/emailtemplates/*", recursive=True)
    list_of_mails_type = CreateEmail.objects.all()
    list_of_used_names = []
    for mail_type in list_of_mails_type:
        list_of_used_names.append(mail_type.nom_du_mail_type)
    listdata = []
    listdico = []
    numberfile = 0
    for filename in templateslist:
        linesdata = []
        dicosymb = {}
        dicodata = {}
        listiternames = []
        listiteradjango = []
        listiteraredirect = []
        templateslist[numberfile] = templateslist[numberfile].replace("app3_messaging/templates/app3_messaging/emailtemplates/", "")
        templateslist[numberfile] = templateslist[numberfile].replace(".html", "")
        with open(filename, 'r', encoding='utf-8') as file:
            for line in file:
                data = line
                data = data.replace("[[ domainstatic ]]", param.STATIC_URL)
                # rend l'image visible lors du rendu du gabarit
                linesdata.append(data)
                pattern = re.compile(r'¤(\w+)¤')
                finds = re.findall(pattern, data)
                if finds:
                    listiternames.extend(finds)
                patterndjango = re.compile(r'%%(\w+)%%')
                findsdjango = re.findall(patterndjango, data)
                if findsdjango:
                    listiteradjango.extend(findsdjango)
                patternredirect = re.compile(r'µ(\w+)µ')
                findsredirect = re.findall(patternredirect, data)
                if findsredirect:
                    listiteraredirect.extend(findsredirect)
        data = ''.join(linesdata)
        dicosymb["NAME"] = templateslist[numberfile]
        dicosymb["LIST"] = listiternames
        dicosymb["LIST2"] = listiteradjango
        dicosymb["LIST3"] = listiteraredirect
        dicodata["NAME"] = templateslist[numberfile]
        dicodata["LIST"] = data
        listdico.append(dicosymb)
        listdata.append(dicodata)
        numberfile += 1
    dicosymbdjango = textprocess.possivardjango()
    sent = False
    if request.method == 'POST':
        form = CreateEmailForm(request.POST)
        if form.is_valid():
            nomsymb = []
            nomsymbdjango = []
            link_redirect = []
            data = dict(request.POST.items())
            templatefilename = data["templatefilename"]
            nomdumailtype = data["nom_du_mail_type"]
            nomdumailtype = textprocess.convert_string(nomdumailtype)
            try:
                nomsymb = request.POST.getlist("nomsymb[]")
            except KeyError:
                pass
            try:
                nomsymbdjango = request.POST.getlist("nomsymbdjango[]")
            except KeyError:
                pass
            try:
                link_redirect = request.POST.getlist("linkredirect[]")
            except KeyError:
                pass
            domain = param.PUBLIC_SITE
            content = textprocess.emailrender(templatefilename, nomsymb, nomsymbdjango, domain, link_redirect)
            add_to_data = CreateEmail(content=content, nom_du_mail_type=nomdumailtype)
            add_to_data.save()
            sent = True
    else:
        form = CreateEmailForm()

    context = {"tinymce_key": param.TINYMCE_KEY, "user": connected_user, "dicofilesymbname": listdico,
               "usednames": list_of_used_names, "filedata": listdata, "djangovar": dicosymbdjango,
               "sent": sent, "form": form}

    # log_mails.debug(f" list data are : {listdata}")
    # BUG listdata contains something which generate the 404 error
    return render(request, 'app3_messaging/mails_template_create.html', context)


@login_required
@permission_required('app0_access.view_communication')
def mails_send(request):
    if 'log_mails' not in globals():
        global log_mails
        log_mails = Logger('mails', level=logging.ERROR, file=False).run()
    users = get_users(type_of_order_by='last_name', exclude_prospects=True, exclude_no_email=True)
    users_list = []
    for user in users:
        try:
            if user.profile.subscribe_emails:
                users_list.append(user)
        except Profile.DoesNotExist:
            users_list.append(user)
    groupslist = []
    allgroups = Group.objects.all().exclude(permissions__codename__in=['view_prospect', ]).order_by(Lower('name'))
    allprospectsgroupes = Group.objects.all().filter(permissions__codename__in=['view_prospect', ])
    connected_user = ''
    for people in users_list:
        query_set = Group.objects.filter(user=people)
        groupslist.append(query_set)
    if request.user.is_authenticated:
        connected_user = User.objects.get(pk=request.user.id)
    templatelist = CreateEmail.objects.all()
    listdico = []
    for template in templatelist:
        content = template.content
        dicotemplate = {"NAME": template.nom_du_mail_type, "LIST": content}
        listdico.append(dicotemplate)
    list_campaign = Campaign.objects.filter(nom_de_la_campagne__isnull=False)
    compiled_users = zip(users_list, groupslist)
    form = CreateCampaignForm()
    sent = False
    context = {"tinymce_key": param.TINYMCE_KEY, "user": connected_user, "allgroups": allgroups,
               "allprospects": allprospectsgroupes, "compiledusers": compiled_users, "templates": listdico,
               "listcampaign": list_campaign, "form": form}
    if request.method == 'POST':
        form = CreateCampaignForm(request.POST)
        if "createcampaign" in request.POST:
            data, createemail, key, recipients, subject = textprocess.get_info(request)
            campaign_name = data["nom_de_la_campagne"]
            createcampaign(subject, connected_user.email, recipients, createemail, name=campaign_name, has_name=True)
            context = {"tinymce_key": param.TINYMCE_KEY, "user": connected_user, "allgroups": allgroups,
                       "compiledusers": compiled_users, "templates": listdico, "listcampaign": list_campaign,
                       "form": form}
        if "sendcampaign" in request.POST:
            data = dict(request.POST.items())
            campaign = data["campaign_id"]
            log_mails.debug(f"Campaign ID is {campaign}")
            number_to_send = data["number_to_send"]
            said_campaign = DataEmail.objects.filter(
                campaign_of_mail=campaign).filter(date_sent=None)[:int(number_to_send)]
            key = Campaign.objects.get(pk=campaign).mail_type.id
            content = CreateEmail.objects.get(pk=key).content
            istoobig, listemail = textprocess.func_istoobig(said_campaign, content, lot=number_to_send)
            context = {"tinymce_key": param.TINYMCE_KEY, "user": connected_user, "allgroups": allgroups,
                       "compiledusers": compiled_users, "templates": listdico, "listemail": listemail,
                       "form": form, "campaign_id": campaign, "istoobig": istoobig, "id_mail_type": key,
                       "listcampaign": list_campaign}
        if "envoidemail" in request.POST:
            data, createemail, key, recipients, subject = textprocess.get_info(request)
            listemails, campaign_id = createcampaign(subject, connected_user.email, recipients, createemail)
            content = CreateEmail.objects.get(pk=key).content
            istoobig, listemailcontent = textprocess.func_istoobig(listemails, content)
            context = {"tinymce_key": param.TINYMCE_KEY, "user": connected_user, "allgroups": allgroups,
                       "compiledusers": compiled_users, "templates": listdico, "listemail": listemailcontent,
                       "campaign_id": campaign_id, "istoobig": istoobig, "id_mail_type": key}
        if "aperçuenvoidemail" in request.POST:
            maillist = []
            key = request.POST.get("id_mail_type")
            if "listemailtoobig" not in request.POST:
                try:
                    maillistkey = request.POST.getlist("mailstosend[]")
                    maillist = DataEmail.objects.filter(clef__in=maillistkey)
                except KeyError:
                    pass
            else:
                campaign_id = request.POST.get("listemailtoobig")
                number_to_send = request.POST.get("istoobignumber")
                maillist = DataEmail.objects.filter(
                    campaign_of_mail=campaign_id).filter(date_sent=None)[:int(number_to_send)]
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_in_executor(None, sendcampaign, maillist, key)
            sent = True
            context = {"tinymce_key": param.TINYMCE_KEY, "user": connected_user, "allgroups": allgroups,
                       "compiledusers": compiled_users, "allprospects": allprospectsgroupes, "templates": listdico,
                       "listcampaign": list_campaign, "form": form, "sent": sent}
    return render(request, 'app3_messaging/mails_template_send.html', context)


@login_required
@permission_required('app0_access.view_communication')
def mails_manage(request):
    connected_user = ''
    # disabled: not functional
    if request.user.is_authenticated:
        connected_user = User.objects.get(pk=request.user.id)
    if request.method == 'POST':
        if "managemail" in request.POST:
            templates_names = []
            data = dict(request.POST.items())
            try:
                templates_names = request.POST.getlist("templates_names[]")
            except KeyError:
                pass
            if data["rename"] != '':
                rename = data["rename"]
                rename = textprocess.convert_string(rename)
                createemail = CreateEmail.objects.get(nom_du_mail_type=templates_names[0])
                createemail.nom_du_mail_type = rename
                createemail.save()
            try:
                if "delete" in data:  # test if ordered to delete. if yes continue, if not then KeyError.
                    for template in templates_names:  # if yes, take all selected templates then delete them
                        a = CreateEmail.objects.get(nom_du_mail_type=template)
                        a.delete()
            except KeyError:
                pass
        if "managecampaign" in request.POST:
            campaigns_names = []
            data = dict(request.POST.items())
            try:
                campaigns_names = request.POST.getlist("campaigns_names[]")
            except KeyError:
                pass
            if data["rename_campaign"] != '':
                rename = data["rename_campaign"]
                rename = textprocess.convert_string(rename)
                renamecampaign = Campaign.objects.get(nom_de_la_campagne=campaigns_names[0])
                renamecampaign.nom_de_la_campagne = rename
                renamecampaign.save()
            try:
                if "delete_campaign" in data:  # test if ordered to delete. if yes continue, if not then KeyError.
                    for campaign in campaigns_names:  # if yes, take all selected templates then delete them
                        a = Campaign.objects.get(nom_de_la_campagne=campaign)
                        a.delete()
            except KeyError:
                pass

    templatelist = CreateEmail.objects.all()
    listdico = []
    for template in templatelist:
        dicotemplate = {"NAME": template.nom_du_mail_type, "LIST": template.content}
        listdico.append(dicotemplate)
    list_campaign = Campaign.objects.filter(nom_de_la_campagne__isnull=False)
    context = {"tinymce_key": param.TINYMCE_KEY, "user": connected_user,
               "templates": listdico, "campaigns": list_campaign}
    return render(request, 'app3_messaging/mails_template_manage.html', context)


@login_required
@permission_required('app0_access.view_communication')
def mails_mailbox(request):
    if 'log_mailbox' not in globals():
        global log_mailbox
        log_mailbox = Logger('log_mailbox_c', level=logging.ERROR).run()

    t = time.time()
    connected_user = ''
    if request.user.is_authenticated:
        connected_user = User.objects.get(pk=request.user.id)

    all_campaigns = Campaign.objects.all().order_by("-id")
    compiled_campaigns = []
    for page_campaign in all_campaigns:
        count = page_campaign.dataemail_set.all().count()
        dataemails = page_campaign.dataemail_set.all()[:10]
        contents = []
        for dataemail in dataemails:
            contents.append([dataemail.user, dataemail])
        compiled_campaigns.append([page_campaign, contents, count])

    paginator_campaign = Paginator(compiled_campaigns, 25)
    page_number_campaign = request.GET.get('page_campaign')
    page_obj_campaign = paginator_campaign.get_page(page_number_campaign)

    context = {"tinymce_key": param.TINYMCE_KEY, "user": connected_user, "page_obj_campaign": page_obj_campaign}
    duration = time.time() - t
    log_mailbox.debug(f"TIMER VIEW: {duration}")
    t2 = time.time()
    r = render(request, 'app3_messaging/mails_template_mailbox.html', context)
    duration2 = time.time() - t2
    log_mailbox.debug(f"TIMER TEMPLATE: {duration2}")
    return r

#  ---------------------------------------- DEBUT LIENS MAILS/ FIN MAILS -----------------------------------------------


def lien_unsubscribe(request, clef):
    datenow = timezone.now()
    unsubscribed = False
    if request.method == 'POST':
        if "unsubscribe" in request.POST:
            try:
                get_user = DataEmail.objects.get(clef=clef)
                get_user.date_unsubscribed = datenow
                get_user.save()
                profile = Profile.objects.get(user=get_user.user.id)
                profile.subscribe_emails = False
                profile.save()
                if not get_user.is_notif:
                    campaign = Campaign.objects.get(id=get_user.campaign_of_mail.id)
                    campaign.number_unsubscribed += 1
                    campaign.save()
                unsubscribed = True
            except DataEmail.DoesNotExist:
                pass
    context = {"tinymce_key": param.TINYMCE_KEY, "unsubscribed": unsubscribed}
    return render(request, 'app3_messaging/mails_unsubscribe.html', context)


def lien_peculiar_click(request, clef, url_encoded):
    if 'log_link' not in globals():
        global log_link
        log_link = Logger('log_link', level=logging.WARNING, file=True).run()
    datenow = timezone.now()
    log_link.debug(f"link entry {url_encoded}")
    try:
        add_to_log = DataEmail.objects.get(clef=clef)
        if not add_to_log.date_clicked:
            add_to_log.date_clicked = datenow
            add_to_log.save()
            log_link.debug(f"link date_clicked added")
        if not add_to_log.is_notif:
            log_link.debug(f"link is not from notif")
            test = Campaign.objects.get(id=add_to_log.campaign_of_mail.id)
            test.number_clicked += 1
            test.save()
        domain = urlparse(url_encoded).netloc
        log_link.debug(f"got domain: {domain}")
        if any(item in domain for item in ["protecia", "serenicia", "localhost"]):
            # print(True)
            log_link.debug(f"link has correct domain")
            if abs(datenow - add_to_log.date_clicked).days < 7:
                login(request, add_to_log.user, backend='django.contrib.auth.backends.ModelBackend')
                log_link.debug(f"User has been logged in")
    except DataEmail.DoesNotExist:
        pass
    return redirect(url_encoded)


def lien_peculiar(request, clef):
    datenow = timezone.now()
    try:
        add_to_log = DataEmail.objects.get(clef=clef)
        if not add_to_log.date_opened:
            add_to_log.date_opened = datenow
            add_to_log.save()
            if not add_to_log.is_notif:
                test = Campaign.objects.get(id=add_to_log.campaign_of_mail.id)
                test.number_opened += 1
                test.save()
    except DataEmail.DoesNotExist:
        pass
    return redirect(param.STATIC_URL + "app3_messaging/images/Solid_white.png")

