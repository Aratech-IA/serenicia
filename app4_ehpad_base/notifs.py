from django.contrib.auth.models import User
from app3_messaging.utils import get_users
from app3_messaging.mails import sendnotif
from app3_messaging.tokens import account_activation_token
import logging
from app1_base.log import Logger
from django.conf import settings
from django.urls import reverse
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.utils.translation import gettext_lazy as _

if 'log_mails_notif' not in globals():
    global log_mails_notif
    log_mails_notif = Logger('mails_notifs', level=logging.ERROR, file=True).run()

constance_martin = "Constance Martin <constance.martin@serenicia.net>"
# "Amelie <constance.martin@serenicia.net>"


# C'est quoi ce truc ? A enlever ?
def send_welcome_email(instance):  # app4_ehpad_base
    log_mails_notif.debug(f"step 1 {instance}")
    link_redirect = ""
    sendnotif(_("Welcome !"), "welcome_staff_email", [instance.email, ], [],
              [link_redirect, ], ["Username"], constance_martin,
              files=["app3_messaging/files/2020_mars_L.A.pdf",
                     "app3_messaging/files/2020_Version_Fevrier_Livret_de_prise_de_poste.pdf",
                     "app3_messaging/files/Fiche_Salarie.pdf"],
              symbflexnames=False)


def send_notif_new_photo_to_family(folder):  # app4_ehpad_base
    log_mails_notif.debug(f"step 1")
    resident = User.objects.get(profileserenicia__folder=folder)
    log_mails_notif.debug(f"step 2 {resident}")
    mails = [user.email for user in User.objects.filter(profileserenicia__user_list__user=resident,
                                                        groups__permissions__codename='view_family',
                                                        profile__preferencesserenicia__notif_family_new_picture=True,
                                                        is_active=True) if user.email]
    log_mails_notif.debug(f"step 3 {mails}")
    sendnotif(_('New pic available'), "notif_new_photo", mails, [_('A new pic of'), resident.get_full_name()],
              [reverse("Gallery")], ["First Name"], constance_martin)


def send_notif_doctor():  # app4_ehpad_base
    log_mails_notif.debug(f"step 1")
    recipients_email = get_users(perms=['view_doctor', ], exclude_no_email=True, exclude_prospects=True)
    recipients_email = recipients_email.exclude(profile__preferencesserenicia__notif_doctor_demand_date=False)
    log_mails_notif.debug(f"step 2 {recipients_email}")
    days_nb = [1, 2, 3, 4, 5]
    for recipient in recipients_email:
        log_mails_notif.debug(f"step 3 {recipient}")
        log_mails_notif.debug(f"step 3-2 {recipient.email}")
        links_redirect = []
        for nb in days_nb:
            links_redirect.append(reverse("add_date_doctor", kwargs={'doctor': recipient.id, 'day': nb}))
        log_mails_notif.debug(f"step 4 {links_redirect}")
        sendnotif(_("Request dates of passage"), "doctor_passage_date", [recipient.email, ],
                  [_("What day would you like to come ?")], links_redirect, ["Civility", "Last Name", "First Name"],
                  constance_martin)