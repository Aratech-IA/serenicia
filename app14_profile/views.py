import glob

from django.conf import settings
from django.shortcuts import render, redirect
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ObjectDoesNotExist

from django.contrib import messages
from django.contrib.auth.decorators import login_required

from django.contrib.auth.models import User
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm

from .forms import UserForm, ProfileForm, ProfileSereniciaForm

from app4_ehpad_base.forms_documents import UploadCard
from app4_ehpad_base.models import Card, PayRoll


@login_required
def profile(request):
    if not request.user.has_perm('app0_access.view_family'):
        try:
            request.session.pop('resident_id')
        except KeyError:
            pass
    video = False

    national_card = Card.objects.filter(type_card='national_card', user_resident=User.objects.get(pk=request.user.id))

    if len(glob.glob(settings.MEDIA_ROOT + "/videos_users/" + request.user.profileserenicia.folder + "/*.mp4")) != 0:
        video = settings.MEDIA_URL + "videos_users/" + request.user.profileserenicia.folder + "/" + request.user.profileserenicia.folder + ".mp4"
    try:
        payroll = PayRoll.objects.filter(employees=request.user)
        payroll_list = [
            {
                'date': f'{payslip.date_of_payslip.month}/{payslip.date_of_payslip.year}',
                'payslip': f'{settings.MEDIA_URL}{str(payslip.payslip)}'
            } for payslip in payroll
        ]
    except ObjectDoesNotExist:
        payroll_list = False

    if request.method == 'POST':
        user_form = UserForm(request.POST, instance=request.user)
        profile_form = ProfileForm(request.POST, instance=request.user.profile)
        profile_serenicia_form = ProfileSereniciaForm(
            request.POST, request.FILES, instance=request.user.profileserenicia
        )
        form_upload_card = UploadCard(request.POST, request.FILES)

        if form_upload_card.is_valid():
            instance = form_upload_card.save(commit=False)
            instance.user_resident = User.objects.get(pk=request.user.id)
            data = form_upload_card.cleaned_data
            Card.objects.update_or_create(
                type_card=data['type_card'], user_resident=instance.user_resident, active=True, defaults=data
            )
            return redirect('profile')

        if user_form.is_valid() and profile_serenicia_form.is_valid():
            user_form.save()
            profile_serenicia_form.save()

        if profile_form.is_valid():
            profile_form.save()

            messages.success(request, _('Your information has been change'), extra_tags='success')
            return redirect('profile')

    else:
        form_upload_card = UploadCard()
        user_form = UserForm(instance=request.user)
        profile_form = ProfileForm(instance=request.user.profile)
        profile_serenicia_form = ProfileSereniciaForm(instance=request.user.profileserenicia)

    context = {
        'video': video, 'form_upload_card': form_upload_card, 'national_card': national_card,
        'user_form': user_form, 'profile_form': profile_form, 'profile_serenicia_form': profile_serenicia_form,
        'payroll': payroll_list,
    }

    return render(request, 'app14_profile/profile.html', context)


@login_required
def change_password(request):
    if request.method == 'POST':
        password_form = PasswordChangeForm(request.user, request.POST)

        if password_form.is_valid():
            user = password_form.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Password was successfully updated', extra_tags='success')
            return redirect('profile')
    else:
        password_form = PasswordChangeForm(request.user)

    return render(request, 'app14_profile/change_password.html', {'password_form': password_form})