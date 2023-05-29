import glob
import re
import time
import asyncio
import logging

from urllib.parse import urlparse
from asgiref.sync import sync_to_async, async_to_sync
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.core.paginator import Paginator
from django.template.defaultfilters import lower
from django.urls import reverse
from django.utils import timezone
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.utils.encoding import force_str, force_bytes
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.models import Group, User
from django.contrib.auth import login
from django.conf import settings as param

from app3_messaging.tokens import account_activation_token
from app3_messaging.mails import sendcampaign, createcampaign
from app3_messaging.notifs import send_notif_activation_account
from app1_base.models import Profile, ProfileSecurity
from app3_messaging.forms import SignUpForm
import app3_messaging.textprocess as textprocess
from app1_base.log import Logger


# The model used for this app depend on the domain Protecia or Serenicia, we need to get the correct model.
if "protecia" in param.DOMAIN.lower():
    model_linked = ProfileSecurity
else:
    from app4_ehpad_base.models import ProfileSerenicia
    model_linked = ProfileSerenicia


def register(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            data = dict(request.POST.items())
            try:
                user = User.objects.get(username=(lower(data["last_name"] + "." + data["first_name"])))
                # print(user, (lower(data["last_name"] + "." + data["first_name"])))
            except User.DoesNotExist:
                # print("user does not exist", (lower(data["last_name"] + "." + data["first_name"])))
                user = User.objects.create_user(lower(data["last_name"] + "." + data["first_name"]),
                                                data["email"],
                                                data["password1"])
                user.is_active = False
                user.first_name = data["first_name"]
                user.last_name = data["last_name"]
                user.save()
                # print("User created:", user)
                profile = Profile(user=user)
                profile.save()
                # print("Profile created:", profile)
                profile_j = model_linked(user=user)
                profile_j.save()
                # print("Profile linked created:", profile_j)
                send_notif_activation_account(user)
                # envoi email + inclus token redirection --> voir bashing
                return redirect('account_activation_sent_simple', user.pk)
    else:
        form = SignUpForm()
    context = {"form": form}
    return render(request, 'app5_ehpad_messaging/registration/register_new_user.html', context)


def account_activation_sent(request, user):
    user = User.objects.get(pk=user)
    validated = False
    sent = False
    if request.method == 'POST':
        if "re-send" in request.POST:
            if not user.is_active:
                send_notif_activation_account(user)
                sent = True
            else:
                validated = True

    context = {"user": user, "validated": validated, "sent": sent}
    return render(request, 'app5_ehpad_messaging/registration/account_activation_email.html', context)


def activate(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and account_activation_token.check_token(user, token):
        user.is_active = True
        user.save()
        login(request, user, backend='django.contrib.auth.backends.ModelBackend')
        return redirect('/')
    else:
        if not (user is not None):
            reason = _("The user does not exist")
        elif not account_activation_token.check_token(user, token):
            reason = _("The activation link is invalid or the user account is not activated")
        else:
            reason = _("unknown reason")
        context = {"reason": reason}
        return render(request, 'app5_ehpad_messaging/registration/register_invalid_activate_user.html', context)
