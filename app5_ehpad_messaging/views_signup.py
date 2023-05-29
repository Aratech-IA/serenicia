import logging

from django.conf import settings
from django.contrib import messages
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.shortcuts import render, redirect
from django.contrib.auth.models import Group, User
from django.urls import reverse

from django.utils.translation import gettext_lazy as _

from app1_base.log import Logger

from app4_ehpad_base.api_netsoins import create_username

from app3_messaging.models import Notification
from app5_ehpad_messaging.models import TempAssignation
from app5_ehpad_messaging.forms import SignUpFormResident, SignUpFormFamily, SignUpFormEmployee, ProfileSignUpForm, \
    ProfileSerenSignUpForm, ProfileEhpadForm, ResidentDemandForm

if 'log_views_app5_ehpad_messaging' not in globals():
    global log_login
    log_login = Logger('log create account', level=logging.ERROR).run()


# def register(request):
#     if request.method == 'POST':
#         form = SignUpForm(request.POST)
#         if form.is_valid():
#             data = dict(request.POST.items())
#             try:
#                 user = User.objects.get(username=(lower(data["last_name"] + "." + data["first_name"])))
#                 # print(user, (lower(data["last_name"] + "." + data["first_name"])))
#             except User.DoesNotExist:
#                 # print("user does not exist", (lower(data["last_name"] + "." + data["first_name"])))
#                 user = User.objects.create_user(lower(data["last_name"] + "." + data["first_name"]), data["email"], data["password1"])
#                 user.is_active = False
#                 user.first_name = data["first_name"]
#                 user.last_name = data["last_name"]
#                 user.save()

#                 profile = Profile(user=user)
#                 profile.save()

#                 profile_j = ProfileSerenicia(user=user)
#                 profile_j.save()

#                 send_notif_activation_account(user)
#                 # envoi email + inclus token redirection --> voir bashing
#                 return redirect('account_activation_sent', user.pk)
#     else:
#         form = SignUpForm()
#     context = {"form": form}
#     return render(request, 'app5_ehpad_messaging/registration/register_new_user.html', context)


def notifinscription(user_id):
    link = reverse('modify user', kwargs={'user_id': user_id})

    phrase1 = _("A person registered on")
    phrase2 = _("Click here and activate their account")
    subject = _("New registration to be validated")
    content = f"{phrase1} Serenicia.<br><a href='{link}'>{phrase2}</a>"
    user = User.objects.filter(groups__permissions__codename='view_rightsmanagement')

    Notification.objects.create(subject=subject, content=content).recipients.add(*user)


def register_user(request, mod):
    message = str('')
    message_user = str(_('A user with this'))
    already_exists = str(_('already exists'))
    messages_success = str(_('Your account has been created, your login data has been sent to you by email'))
    if request.method == 'POST':
        if mod == 'resident':
            data = {'password1': 'serenicia26', 'password2': 'serenicia26',
                    'first_name': request.POST.get('first_name'), 'last_name': request.POST.get('last_name'),
                    'email': request.POST.get('email')}
            form = SignUpFormResident(data)
        elif mod == 'family':
            form = SignUpFormFamily(request.POST)
        else:
            form = SignUpFormEmployee(request.POST)

        form_profile = ProfileSignUpForm(request.POST)
        form_profile_j = ProfileSerenSignUpForm(request.POST)
        form_profile_ehpad = ProfileEhpadForm(request.POST)
        form_relation = ResidentDemandForm(request.POST)

        if form.is_valid() and form_profile.is_valid() and form_profile_j.is_valid():
            user = form.save(commit=False)
            if mod == 'family' or mod == 'employee':
                email = form.cleaned_data.get('email')
                if User.objects.filter(email=email).exists():
                    log_login.debug(f"User already exist")
                    message = f"{message_user} {_('email')} {email} {already_exists}."
                    messages.error(request, message, extra_tags='error')
                    return redirect('register_user', mod=mod)
                username = create_username(last_name=user.last_name, first_name=user.first_name)
                homonym = User.objects.filter(last_name__iexact=user.last_name, first_name__iexact=user.first_name)
                if homonym.exists():
                    username = f"{username}.{homonym.count()}"
            else:
                username = create_username(last_name=user.last_name, first_name=user.first_name, resident=True)
            user.username = username
            user.save()
            profile = form_profile.save(commit=False)
            profile.user = user
            profile.save()
            profile_j = form_profile_j.save(commit=False)
            profile_j.user = user
            profile_j.save()
            if mod == 'employee':  # MOD EMPLOYEE/COLLABORATOR
                group = form.cleaned_data['group']
                try:
                    user.groups.add(group)
                    user.is_active = False
                    user.save()
                except Exception as error:
                    log_login.debug(f"Add employee to group: {error}")
            if mod == 'family':
                try:
                    family_group = Group.objects.get(permissions__codename='view_family')
                    user.groups.add(family_group)
                    user.is_active = False
                    user.save()
                    # send_notif_activation_account(user)
                except Exception as error:
                    log_login.debug(f"User group family: {error}")
                form_relation = ResidentDemandForm(request.POST)
                if form_relation.is_valid():
                    last_name = form_relation.cleaned_data['last_name_of_resident']
                    first_name = form_relation.cleaned_data['first_name_of_resident']
                    try:
                        resident = User.objects.get(last_name__iexact=last_name, first_name__iexact=first_name,
                                                    groups__permissions__codename='view_residentehpad'
                                                    )
                        user.profileserenicia.user_list.add(resident.profile)
                    except (ObjectDoesNotExist, MultipleObjectsReturned):
                        TempAssignation.objects.create(demander=user, last_name=last_name, first_name=first_name)
                notifinscription(user.id)
                log_login.debug(f"New user {mod} created")
                messages.success(request, _(messages_success), extra_tags='success')
                return redirect('register_user', mod=mod)
            if mod == 'resident':  # MOD RESIDENT
                profile_j.user_list.add()
                try:
                    # Ne marche que pour les résidents EHPAD - résident RSS = view_resident
                    resident_group = Group.objects.get(permissions__codename='view_residentehpad')
                    user.groups.add(resident_group)
                    user.is_active = False
                    user.save()
                except Exception as error:
                    log_login.debug(f"User group resident: {error}")
                if 'add_family' in request.POST:
                    return redirect('register_user', mod=mod)
                form_profile_ehpad = ProfileEhpadForm(request.POST)
                if form_profile_ehpad.is_valid():
                    profile_ehpad = form_profile_ehpad.save(commit=False)
                    profile_ehpad.resident = user
                    profile_ehpad.save()
                else:
                    log_login.debug(f"Form error: {form_profile_ehpad.errors}")
            notifinscription(user.id)
            log_login.debug(f"New user {mod} created")
            messages.success(request, _(messages_success), extra_tags='success')
            return redirect('register_user', mod=mod)
        else:
            pass
            #  ERROR MESSAGE AND REDIRECT PATH
            if form.errors:
                log_login.debug(f"User form error: {form.errors}")
                message = form.errors

            if form_profile.errors:
                log_login.debug(f"Profile form error: {form_profile.errors}")
                message = form_profile.errors

            if form_profile_j.errors:
                log_login.debug(f"Profile Serenicia form error: {form_profile_j.errors}")
                message = form_profile_j.errors

            if mod == 'family':
                messages.error(request, f"{message}", extra_tags='error')

            if mod == 'employee':
                messages.error(request, f"{message}", extra_tags='error')

            if mod == 'resident':
                messages.error(request, f"{message}", extra_tags='error')
    else:
        if mod == 'resident':
            form = SignUpFormResident()
        elif mod == 'family':
            form = SignUpFormFamily()
        else:
            form = SignUpFormEmployee()

        form_profile = ProfileSignUpForm()
        form_relation = ResidentDemandForm()
        form_profile_ehpad = ProfileEhpadForm()
        form_profile_j = ProfileSerenSignUpForm()
    context = {
        'mod': mod, 'form': form, 'form_profile_ehpad': form_profile_ehpad, 'form_profile': form_profile,
        'form_profile_j': form_profile_j, 'form_relation': form_relation,
    }
    return render(request, 'app5_ehpad_messaging/registration/register_user.html', context)

