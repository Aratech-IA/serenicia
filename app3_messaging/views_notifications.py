import glob
import re
import time
import asyncio
import logging

from urllib.parse import urlparse
from asgiref.sync import sync_to_async, async_to_sync
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponse
from django.shortcuts import render, redirect
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

from app3_messaging.models import Notification
from app3_messaging.views_messaging import internal_emailing_mailbox
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


@login_required
def notifs_mailbox(request):
    if not request.user.has_perm('app0_access.view_family'):
        try:
            request.session.pop('resident_id')
        except KeyError:
            pass
    # send_notif_doctor()
    connected_user = ''
    if request.user.is_authenticated:
        connected_user = User.objects.get(pk=request.user.id)
    notifs = Notification.objects.filter(recipients=connected_user).order_by("-date_sent")
    paginator_received = Paginator(notifs, 25)
    page_number_received = request.GET.get('page_received')
    page_obj_received = paginator_received.get_page(page_number_received)
    context = {"page_obj_received": page_obj_received, "user": connected_user}
    return render(request, 'app3_messaging/notifs_mailbox.html', context)


@login_required
def notifs_opened(request):
    if request.method == 'POST':
        data = request.POST.items()
        for item in data:
            notif = Notification.objects.get(id=item[0])
            notif.list_opened.add(request.user.id)
            notif.save()
            # print(notif.list_opened.all())
    return redirect(internal_emailing_mailbox)


@login_required
def notif_read(request, notif_id):
    if request.method == 'GET':
        try:
            notif = Notification.objects.get(id=notif_id)
            notif.list_opened.add(request.user)
            notif.save()
        except ObjectDoesNotExist:
            pass
    return HttpResponse(status=200)