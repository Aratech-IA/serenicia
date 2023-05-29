from django.contrib.auth.models import User
from app3_messaging.utils import get_users
from app3_messaging.mails import sendnotif
from app3_messaging.tokens import account_activation_token
import logging
from app1_base.log import Logger
from django.conf import settings
from django.urls import reverse
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.utils.translation import gettext_lazy as _

# "Amelie <constance.martin@serenicia.net>"

if 'log_mails_notif' not in globals():
    global log_mails_notif
    log_mails_notif = Logger('mails_notifs', level=logging.ERROR, file=True).run()

constance_martin = "Constance Martin <constance.martin@serenicia.net>"


def notif_message(recipients_email, connected_user, createemail, user_type):
    log_mails_notif.debug(f"step 1 {recipients_email} | {connected_user}")
    link_redirect = settings.PUBLIC_SITE + reverse("internal_emailing_mailbox")
    log_mails_notif.debug(f"step 2 {link_redirect}")
    if user_type == 'default':
        sendnotif("Message reçu sur Serenicia.!", "notif_message", recipients_email,
                  ["Vous avez reçu un message de", connected_user.username, createemail.subject],
                  [link_redirect, ], ["Username"], constance_martin, )
    else:
        sendnotif("Message reçu sur Serenicia.!", "notif_message", recipients_email,
                  [f"Vous avez reçu un message en {user_type} de", connected_user.username, createemail.subject],
                  [link_redirect, ], ["Username"], constance_martin, )


def notif_message_cc(recipients_email, connected_user, createemail):
    log_mails_notif.debug(f"step 1 CC {recipients_email} | {connected_user}")
    link_redirect = settings.PUBLIC_SITE + reverse("internal_emailing_mailbox")
    log_mails_notif.debug(f"step 2 CC {link_redirect}")
    sendnotif("Message reçus sur Serenicia.!", "notif_message", recipients_email,
              ["Vous avez reçus un message en CC de", connected_user.username, createemail.subject],
              [link_redirect, ], ["Username"], constance_martin)


def send_notif_activation_account(user):
    log_mails_notif.debug(f"step 1 {user}")
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    link_redirect = "appmail/activate/" + uid + "/" + account_activation_token.make_token(user)
    log_mails_notif.debug(f"step 2 {link_redirect}")
    sendnotif(_("Confirmation of the e-mail address"), "confirmation_email", [user.email, ], [],
              [link_redirect, link_redirect], ["Username"],
              constance_martin, symbflexnames=False)


