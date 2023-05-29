import glob
import re
import datetime
import asyncio
import logging

from django.db.models.functions import Lower
from django.contrib.auth.models import User
from django.conf import settings as param

from app1_base.models import ProfileSecurity
from app3_messaging.models import *

# The model used for this app depend on the domain Protecia or Serenicia, we need to get the correct model.
if "protecia" in param.DOMAIN.lower():
    model_linked = ProfileSecurity
else:
    from app4_ehpad_base.models import ProfileSerenicia

    model_linked = ProfileSerenicia


def get_users(perms: list = False, type_of_order_by: str = False, exclude_prospects: bool = False,
              connected_user_pk: str = False, exclude_no_first_connection: bool = False,
              exclude_no_email: bool = False, exclude_unsubscribed: bool = True, exclude_mass_mailing: bool = True, ):
    users = User.objects.exclude(is_active=False)
    if exclude_no_first_connection:
        users = users.exclude(last_login__isnull=True)
    if exclude_no_email:
        users = users.exclude(email='')
    if exclude_prospects:
        users = users.exclude(groups__permissions__codename__in=['view_prospect', ])
    if connected_user_pk:
        users = users.exclude(pk=connected_user_pk)
    if perms:
        users = users.filter(groups__permissions__codename__in=perms)
    if exclude_unsubscribed:
        users = users.exclude(profile__subscribe_emails=False)
    if exclude_mass_mailing:
        users = users.exclude(groups__permissions__codename__in=['view_massmailing', ])
    if type_of_order_by:
        users = users.order_by(Lower(type_of_order_by))
    return users


def singularize(users):
    new_users = []
    for el in users:
        if el not in new_users:
            new_users.append(el)
    return new_users


def delete_message(request):
    if request.method == 'POST':
        if "delete" in request.POST:
            data = dict(request.POST.items())
            inter = Intermediate.objects.get(id=data['inter_id'])
            inter.is_shown = False
            inter.save()


def test_duplicates_per_sender():
    users = get_users(type_of_order_by='last_name', exclude_prospects=True, exclude_no_email=True,
                      exclude_no_first_connection=True)
    len(users)
    for user in users:
        print(
            f'-------------------------------------------{user.username}---------------------------------------------')
        msgs = IntraEmail.objects.filter(intermediate__user_type='sender', intermediate__recipient=user)
        for msg in msgs:
            start = msg.date_sent - datetime.timedelta(seconds=5)
            end = msg.date_sent + datetime.timedelta(seconds=5)
            duplicates = IntraEmail.objects.filter(content=msg.content, date_sent__range=[start, end]).exclude(
                content='')
            if len(duplicates) > 1:
                print(msg.id, 'duplicates: ', len(duplicates))
            msgs = msgs.exclude(id__in=duplicates)


def duplicate_sender():
    """
    This is for retrieve all the Intermediate id affected by duplicate
    Should not arrive because Marc should have add a unique together

    If you want to filter just do :
    Intermediate.objects.filter(id__in=id).delete()
    """
    query = Intermediate.objects.filter(user_type='sender')
    message_broken = []
    for inter in query:
        nb_inter = Intermediate.objects.filter(recipient=inter.recipient, message=inter.message)
        if nb_inter.count() > 1:
            message_broken.append(nb_inter)
    result = [i.id for q in message_broken for i in q if i.user_type =='default']
    return result


# THIS FUNCTION IS HERE TO TEST DIFFERENCE BETWEEN MIDDLEWARE AND VIEW REQUEST FOR THE INTERNAL EMAILING

# def blabla(username):
#     # in middleware:
#     test_msgs = Intermediate.objects.filter(recipient__username=username, date_opened__isnull=True).exclude(
#         user_type='sender').exclude(is_shown=False)
#     inters_test = Intermediate.objects.filter(recipient__username=username, is_shown=True).exclude(
#         user_type='sender')
#     # in view: (modified for testing)
#     conv = Conversation.objects.filter(intraemail__intermediate__in=inters_test)
#     conv = conv.annotate(nb_msg=Count('intraemail'), last_date=Max('intraemail__date_sent', filter=Q(intraemail__intermediate__is_shown=True)), type=Max('intraemail__intermediate__user_type'))
#     conv = conv.filter(Q(nb_msg__gt=1) | ~Q(type='sender'))
#     msgs = IntraEmail.objects.filter(recipients__username=username, message_conversation__in=conv, intermediate__recipient__username=username, intermediate__is_shown=True, intermediate__user_type__in=['default', 'CC', 'CCI'])
#     test_intras = [inter_test.message for inter_test in inters_test]
#     test_unread_intras = [test_msg.message for test_msg in test_msgs]
#     print('unread not in msgs: ', list(set(test_unread_intras) - set(msgs)))
#     print('not in msgs', list(set(test_intras) - set(msgs)))
#     print('not in test', list(set(msgs) - set(test_intras)))
#     print(len(set(test_intras)), len(set(msgs)))

# def send_test_notif():
#     from app3_messaging.models import IntraEmail
#     from django.contrib.auth.models import User
#     from app3_messaging.notifs import notif_message
#     notif_message(['thomas.poupinet@serenicia.net', ], User.objects.get(username='didier.meyrand'),
#                   IntraEmail.objects.get(id=1709))
