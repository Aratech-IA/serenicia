import json
import logging
import re
import time
import operator
from functools import reduce

from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponse
from django.urls import reverse
from django.utils import timezone
from django.conf import settings as param
from django.shortcuts import render, redirect
from django.db.models import Max, Q, Count
from django.core.paginator import Paginator
from django.utils.translation import gettext_lazy as _

from django.contrib.auth.decorators import login_required

from app1_base.log import Logger
from app3_messaging.utils import delete_message
from app3_messaging.textprocess import htmltotext
from app1_base.models import ProfileSecurity
from app3_messaging.forms import IntraEmailAttachmentForm, CustomGroupCreation
from app3_messaging.models import *

# The model used for this app depend on the domain Protecia or Serenicia, we need to get the correct model.
if "protecia" in param.DOMAIN.lower():
    model_linked = ProfileSecurity
else:
    from app4_ehpad_base.models import ProfileSerenicia

    model_linked = ProfileSerenicia

if 'log_mailbox' not in globals():
    global log_mailbox
    log_mailbox = Logger('log_mailbox', level=logging.DEBUG).run()


def get_timer(now, last, text):
    log_mailbox.debug(f"{text}: {round(now - last, 3)}")
    return now


@login_required
def select_receiver(request, mod):
    if mod == 'new':
        try:
            request.session['selected_receiver'].clear()
            request.session['selected_groups'].clear()
        except KeyError:
            pass
    context = {}
    groups = CustomGroup.objects.order_by(Lower('name'))
    users = User.objects.filter(is_active=True, groups__gt=0, is_superuser=False)\
        .exclude(groups__permissions__codename='view_prospect').exclude(id=request.user.id)
    if request.user.has_perm('app0_access.view_family'):
        users = users.filter(groups__permissions__codename__in=['view_as', 'view_ash', 'view_ide', 'view_practicians',
                                                                'view_family', 'view_manager'],
                             profileserenicia__user_list__user__id=request.session.get('resident_id'),
                             profile__advanced_user=False)
    if request.method == 'POST':
        if request.POST.get('validate'):
            request.session['selected_receiver'] = list(users.filter(id__in=request.POST.getlist('user'))
                                                        .values_list('id', flat=True))
            request.session['selected_groups'] = list(groups.filter(id__in=request.POST.getlist('group'))
                                                      .values_list('id', flat=True))
            return redirect('internal_emailing')
        else:
            if request.POST.get('search-grp'):
                groups = groups.filter(name__icontains=request.POST.get('search-grp'))
                context['searching_grp'] = request.POST.get('search-grp')
            if request.POST.get('search-user'):
                users = users.filter(reduce(operator.and_, (Q(first_name__icontains=name) | Q(last_name__icontains=name)
                                                            for name in request.POST.get('search-user').split(' '))))
                context['searching_user'] = request.POST.get('search-user')
    context['groups'] = groups.order_by(Lower('name'))
    context['users'] = users.order_by(Lower('last_name'), Lower('first_name'))
    return render(request, 'app3_messaging/select_receiver.html', context)


@login_required
def internal_emailing(request):
    context = {}
    connected_user = request.user
    form = IntraEmailAttachmentForm()
    try:
        receiver = list(User.objects.filter(id__in=request.session['selected_receiver']))
    except KeyError:
        receiver = []
    # users = User.objects.filter(is_active=True, groups__gt=0,
    #                             is_superuser=False).exclude(groups__permissions__codename='view_prospect')
    # if connected_user.has_perm('app0_access.view_family'):
    #     users = users.filter(groups__permissions__codename__in=['view_as', 'view_ash', 'view_ide', 'view_practicians',
    #                                                             'view_family', 'view_manager'],
    #                          profileserenicia__user_list__user__id=request.session.get('resident_id'),
    #                          profile__advanced_user=False)
    def end_view():
        # context.update({'compiledusers': sorted(users, key=lambda user: (user.last_name.lower(),
        #                                                                  user.first_name.lower())),
        #                 'allgroups': CustomGroup.objects.order_by(Lower('name')),
        #                 'tags': list(Tag.objects.values_list('name', flat=True))})
        context.update({'tags': list(Tag.objects.values_list('name', flat=True)),
                        'receiver': receiver,
                        'receivercount': len(receiver),
                        'form': form})
        try:
            context['tinymce_key'] = param.TINYMCE_KEY
        except AttributeError:
            context['tinymce_key'] = 'no-api-key'
        return render(request, 'app3_messaging/internal_emailing.html', context)

    if request.method == 'POST':
        if request.POST.get('convo_id'):
            convo = Conversation.objects.get(pk=request.POST['convo_id'])
            context['convo_id'] = convo.id
        else:
            convo = Conversation.objects.create()
        if request.POST.get('message_id'):
            message_answer = IntraEmail.objects.get(id=request.POST.get("message_id"))
            context.update({'message_answer': message_answer,
                            'subject': 'RE:' + message_answer.subject[:117]})
        # if ("envoidemessage" in request.POST) or ("reponsemessage" in request.POST):
        else:
            content = request.POST.get("content")
            subject = request.POST.get("subject")
            max_length = IntraEmail.subject.field.max_length
            form = IntraEmailAttachmentForm(request.POST, request.FILES)

            # recipient_cc = User.objects.filter(username__in=request.POST.getlist("recipientsCC[]")).exclude(
            #     pk=connected_user.pk)
            # recipient_cci = User.objects.filter(username__in=request.POST.getlist("recipientsCCI[]")).exclude(
            #     pk=connected_user.pk)
            if request.POST.get("tags_input"):
                tags = json.loads(request.POST.get("tags_input"))
            else:
                tags = []

            if len(subject) > max_length:
                context.update(
                    {'message': _('Your message subject is too long, please limit it to 120 characters maximum'),
                     'category': _('Error'),
                     'content_text': content,
                     'subject': subject[:max_length],
                     'form': form,
                     # 'receiver': recipient.values_list('username', flat=True),
                     # 'receiverCC': recipient_cc.values_list('username', flat=True),
                     # 'receiverCCI': recipient_cci.values_list('username', flat=True),
                     # 'receivergroup': request.POST.getlist("group_recipients[]"),
                     # 'receivergroupCC': request.POST.getlist("group_recipients_CC[]"),
                     # 'receivergroupCCI': request.POST.getlist("group_recipients_CCI[]"),
                     # 'receivercount': recipient.count() + recipient_cc.count() + recipient_cci.count(),
                     # 'receivercount': receiver.count(),
                     'tags': tags})
                return end_view()
            createemail = IntraEmail.objects.create(subject=subject, content=content, message_conversation=convo,
                                                    content_text=htmltotext(content), date_sent=timezone.now())
            if connected_user.has_perm('app0_access.view_family'):
                createemail.tags.add(Tag.objects.get_or_create(name='family')[0])
            [createemail.tags.add(Tag.objects.get_or_create(name=''.join(re.findall(r'(\w+)', tag["value"])))[0])
             for tag in tags]

            if form.is_valid():
                for file in request.FILES.getlist('attachment'):
                    add_attachment = IntraEmailAttachment(attachment=file, intraemail=createemail)
                    name = add_attachment.attachment.url.split('/')[-1].split('.')[0]
                    add_attachment.name = name
                    add_attachment.save()

            try:
                receiver.remove(connected_user)
            except ValueError:
                pass
            Intermediate.objects.create(message=createemail, recipient=connected_user, user_type='sender')
            Intermediate.objects.bulk_create([Intermediate(message=createemail, recipient=user, user_type='default')
                                              for user in receiver])
            # Intermediate.objects.bulk_create([Intermediate(message=createemail, recipient=user, user_type='CC')
            #                                   for user in recipient_cc])
            # Intermediate.objects.bulk_create([Intermediate(message=createemail, recipient=user, user_type='CCI')
            #                                   for user in recipient_cci])
            context.update({'category': _('Confirmation'), 'message': _('Your message has been sent')})
    context['form'] = IntraEmailAttachmentForm()
    return end_view()


@login_required
def internal_emailing_mailbox(request):
    if not request.user.has_perm('app0_access.view_family'):
        try:
            request.session.pop('resident_id')
        except KeyError:
            pass
    # total = time.time()
    if "reponsemessage" in request.POST:
        return internal_emailing(request)
        # return delete_message(request)
    elif "repondre" in request.POST:
        message_answer = IntraEmail.objects.get(id=request.POST.get("message_id"))
        sender = message_answer.intermediate_set.get(user_type='sender').recipient
        request.session['selected_receiver'] = [sender.id]
        return internal_emailing(request)
    elif 'answer-all' in request.POST:
        message_answer = IntraEmail.objects.get(id=request.POST.get("message_id"))
        request.session['selected_receiver'] = list(message_answer.recipients.values_list('id', flat=True))
        return internal_emailing(request)
    else:
        search = False
        if request.method == 'POST':
            data = dict(request.POST.items())
            if "delete" in request.POST:
                inter = Intermediate.objects.get(id=data['inter_id'])
                inter.is_shown = False
                inter.save()
            if "search_form" in request.POST:
                if data["search"] != '':
                    search = data["search"]
        connected_user = ''
        if request.user.is_authenticated:
            connected_user = User.objects.get(pk=request.user.id)

        inters_test = Intermediate.objects.filter(recipient=connected_user, is_shown=True)
        conv = Conversation.objects.filter(intraemail__intermediate__in=inters_test)
        if search:
            conv = conv.filter(Q(intraemail__tags__name__icontains=search) |
                               Q(intraemail__content_text__icontains=search) |
                               Q(intraemail__subject__icontains=search) |
                               Q(intraemail__recipients__username__icontains=search) |
                               Q(intraemail__recipients__last_name__icontains=search) |
                               Q(intraemail__recipients__first_name__icontains=search))
        conv = conv.annotate(nb_msg=Count('intraemail'),
                             last_date=Max('intraemail__date_sent', filter=Q(intraemail__intermediate__is_shown=True)),
                             type=Max('intraemail__intermediate__user_type'))
        conv = conv.filter(Q(nb_msg__gt=1) | ~Q(type='sender'))
        conv = conv.order_by('-last_date').distinct()
        conv = conv.values_list('id')

        is_sent = False

        paginator_received = Paginator(conv, 15)
        page_number_received = request.GET.get('page_received')
        page_obj_received = paginator_received.get_page(page_number_received)

        msg = IntraEmail.objects.filter(recipients=connected_user,
                                        message_conversation__in=page_obj_received.object_list,
                                        intermediate__recipient=connected_user,
                                        intermediate__is_shown=True)
        if search:
            msg = msg.filter(Q(tags__name__icontains=search) | Q(content_text__icontains=search) |
                             Q(subject__icontains=search) | Q(recipients__username__icontains=search) |
                             Q(recipients__last_name__icontains=search) | Q(recipients__first_name__icontains=search))
        msg = msg.order_by('-date_sent').distinct()
        msg = msg.prefetch_related('intermediate_set', 'intermediate_set__recipient',
                                   'intraemailattachment_set', 'intermediate_set__recipient__profile')
        dict_conv = {key[0]: [] for key in page_obj_received}
        try:
            for m in msg:
                dict_conv[m.message_conversation.id].append(m)
        except KeyError:
            pass
        list_convos = [dict_conv[i[0]] for i in page_obj_received.object_list]

        if request.GET.get('page_sent'):
            is_sent = True

        context = {"tinymce_key": param.TINYMCE_KEY, "user": connected_user, "list_convos": list_convos,
                   "page_obj_received": page_obj_received, "is_sent": is_sent,
                   }
        if search:
            context["search"] = search
        # last = time.time()
        r = render(request, 'app3_messaging/internal_emailing_mailbox.html', context)
        # get_timer(time.time(), last, 'RENDERING')
        # get_timer(time.time(), total, 'TOTAL')
        return r


@login_required
def internal_emailing_mailbox_sent(request):
    # if 'log_mailbox' not in globals():
    #     global log_mailbox
    #     log_mailbox = Logger('log_mailbox', level=logging.ERROR).run()

    # t = time.time()
    if request.method == 'POST':
        if "delete" in request.POST:
            return delete_message(request)
    else:
        connected_user = ''
        if request.user.is_authenticated:
            connected_user = User.objects.get(pk=request.user.id)
        message_sent_recent = IntraEmail.objects.filter(intermediate__user_type='sender',
                                                        intermediate__recipient=request.user.id).order_by('-date_sent')

        # t2 = time.time()
        # duration = t2 - t
        # log_mailbox.debug(f"TIMER VIEW PART 1: {duration}")
        message_sent_recent.reverse()

        paginator_sent = Paginator(message_sent_recent, 25)
        page_number_sent = request.GET.get('page_sent')
        page_obj_sent = paginator_sent.get_page(page_number_sent)
        context = {"tinymce_key": param.TINYMCE_KEY, "user": connected_user, "page_obj_sent": page_obj_sent}

        # t_view = time.time()
        # duration_view = t_view - t
        # log_mailbox.debug(f"TIMER VIEW: {duration_view}")

        r = render(request, 'app3_messaging/internal_emailing_mailbox_sent.html', context)

        # t_render = time.time()
        # duration2 = t_render - t_view
        # log_mailbox.debug(f"TIMER TEMPLATE: {duration2}")
        # duration_total = t_render - t
        # log_mailbox.debug(f"TIMER TOTAL: {duration_total}")

        return r


@login_required
def internal_emailing_conv(request, conv_id):
    # if 'log_mailbox' not in globals():
    #     global log_mailbox
    #     log_mailbox = Logger('log_mailbox', level=logging.ERROR).run()
    if request.method == 'POST':
        if "repondre" in request.POST:
            return internal_emailing(request)
        if "reponsemessage" in request.POST:
            return internal_emailing(request)
        if "delete" in request.POST:
            delete_message(request)
    connected_user = ''
    if request.user.is_authenticated:
        connected_user = User.objects.get(pk=request.user.id)
    # list_msg = []
    conv = Conversation.objects.get(id=conv_id)
    convo = conv.intraemail_set.filter(intermediate__recipient=request.user.id)
    convo = convo.exclude(intermediate__is_shown=False).order_by('-date_sent')
    # print(activity.conv, convo)
    convo = convo.prefetch_related('intermediate_set', 'intermediate_set__recipient',
                                   'message_conversation', 'intraemailattachment_set',
                                   'intermediate_set__recipient__profile')

    is_sent = False

    paginator_received = Paginator(convo, 25)
    page_number_received = request.GET.get('page_received')
    page_obj_received = paginator_received.get_page(page_number_received)

    if request.GET.get('page_sent'):
        is_sent = True

    context = {"tinymce_key": param.TINYMCE_KEY, "user": connected_user,
               "page_obj_received": page_obj_received, "is_sent": is_sent,
               }

    return render(request, 'app3_messaging/internal_emailing_mailbox_conv.html', context)


@login_required
def custom_group_create(request):
    form = CustomGroupCreation(request.POST, None)
    context = {'form': form}
    if request.method == 'POST':
        if form.is_valid():
            grp = form.save()
            return redirect('custom group modify', selected=grp.id)
        else:
            context['invalid'] = reverse('custom group modify',
                                         kwargs={
                                             'selected': CustomGroup.objects.get(name=request.POST.get('name')).id})

    return render(request, 'app3_messaging/custom_group_create.html', context)


@login_required
def custom_group_modify(request, selected):
    context = {}
    try:
        custom_group = CustomGroup.objects.get(id=selected)
        if request.POST.get('delete'):
            custom_group.delete()
            context.update({'message': _('The group has been successfully deleted'), 'category': _('Deleting')})
            raise ObjectDoesNotExist
    except ObjectDoesNotExist:
        context['customgroups'] = CustomGroup.objects.order_by(Lower('name'))
        return render(request, 'app3_messaging/custom_group_modify.html', context)
    groups = Group.objects.all().exclude(permissions__codename__in=['view_prospect', 'view_massmailing']).order_by(
        Lower('name'))
    users = User.objects.filter(groups__id__in=groups, is_active=True, is_superuser=False).order_by(Lower('last_name'),
                                                                                                    Lower('first_name'))
    if request.POST.get('save'):
        selected_groups = groups.filter(id__in=request.POST.getlist('groups'))
        selected_users = users.filter(id__in=request.POST.getlist('users')).exclude(groups__id__in=selected_groups)
        custom_group.name = request.POST.get('name')
        custom_group.groups.set(selected_groups)
        custom_group.members.set(selected_users)
        custom_group.save()
        context.update({'message': _('The modifications has been saved'), 'category': _('Saved')})
    groups = groups.values('id', 'name')
    for group in groups:
        group['users'] = list(User.objects.filter(groups__id=group['id'], is_active=True,
                                                  is_superuser=False).order_by(Lower('last_name'), Lower('first_name'))
                              .values_list('id', flat=True))
    users = users.values('id', 'first_name', 'last_name', 'username', 'profile__photo', 'groups__name')
    # TIMER
    # last = time.time()
    # ----------
    custom_group_users = User.objects.filter(groups__in=custom_group.groups.all(), is_active=True)
    custom_group_users = custom_group_users.union(custom_group.members.filter(is_active=True))
    context.update({'users': users, 'groups': groups,
                    'custom_grp_name': custom_group.name,
                    'custom_grp_users': custom_group_users.order_by(Lower('last_name'), Lower('first_name')).values(
                        'id', 'first_name', 'last_name', 'username', 'profile__photo', 'groups__name'),
                    'groups_id': custom_group.groups.values_list('id', flat=True),
                    'checked': custom_group.members.values_list('id', flat=True),
                    'disabled': users.filter(groups__in=custom_group.groups.all()).values_list('id', flat=True)})
    r = render(request, 'app3_messaging/custom_group_modify.html', context)
    # TIMER
    # last = get_timer(time.time(), last, 'TIMER RENDERING')
    # ----------
    return r


@login_required
def internal_emailing_answer(request):
    internal_emailing_opened(request)
    return redirect(internal_emailing)


def internal_emailing_opened(request, conv_id):
    if request.method == 'GET':
        try:
            convo = Conversation.objects.get(pk=conv_id)
            for message in convo.intraemail_set.filter(recipients=request.user.id):
                mail_inter = message.intermediate_set.get(recipient=request.user.id)
                if not mail_inter.date_opened:
                    mail_inter.date_opened = timezone.now()
                    mail = IntraEmail.objects.get(id=mail_inter.message.id)
                    mail.number_opened += 1
                    mail.save()
                mail_inter.save()
        except ObjectDoesNotExist:
            pass
    return HttpResponse(status=200)
