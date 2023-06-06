""" developed by pierrick-boyer"""

import glob
import logging

from django.conf import settings

from django.contrib import messages
from django.contrib.auth.decorators import login_required

from django.shortcuts import render, redirect

from django.utils import timezone
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from docusign_esign.client.api_exception import ApiException

from .api_docusign import Signature
from .forms_documents import UploadCard, KitInventoryForm, DietForm, ResidentForm, ProfileResidentForm
from .models import Invoice, Card, User, AdministrativeDocument, PersonalizedDocument, KitInventory, Diet

from app1_base.log import Logger
from app14_profile.forms import ProfileSereniciaForm


# ----- LOG ------------------------------------------------------------------------------------------------------------


if 'log_views_doc' not in globals():
    global log_doc
    log_doc = Logger('Views administrative doc', level=logging.ERROR).run()


# ----------------------------------------------------------------------------------------------------------------------


""" Page containing all the invoices of a resident. """


@login_required
def invoice(request):
    user_resident_info = {}
    user_resident = User.objects.get(pk=request.session['resident_id'])

    # User information -> need to check to avoid mistakes
    if user_resident.profile.civility and user_resident.last_name and user_resident.first_name:
        user_resident_info = {
            'civility':
                user_resident.profile.civility,
            'complete_name':
                user_resident.first_name + ' ' + user_resident.last_name,
            'entry_date': user_resident.profileserenicia.entry_date,
        }

    invoices = Invoice.objects.filter(user_resident=user_resident).order_by('-pub_date')
    EHPAD_invoice = Invoice.objects.filter(user_resident=user_resident, type='invoice').order_by('-pub_date')[:8]

    context = {
        'user_resident_info': user_resident_info, 'invoices': invoices, 'EHPAD_invoice': EHPAD_invoice
    }

    return render(request, 'app4_ehpad_base/documents/invoice.html', context)


# ----------------------------------------------------------------------------------------------------------------------


""" Page administrative document regroup : Administrative documents + card of resident (form & result) + delete card """


@login_required
def documents(request):
    user_resident_info = {}

    message_upload = _('Card uploaded successfully. Thank you.')
    button_descriptive_1 = _('Your administrative file is completed, you can consult each document as well and '
                             'download them.')
    button_descriptive_2 = _('The button below allows you to sign all your documents at once, Serenicia uses '
                             'DocuSign to sign your administrative file online. This device allows you to give legal '
                             'value to your signature while complying with the general data protection regulations.')

    user = User.objects.get(pk=request.user.id)
    user_resident = User.objects.get(pk=request.session['resident_id'])

    diet_result = Diet.objects.filter(user_resident=user_resident)

    # User information -> need to check to avoid mistakes
    if user_resident.profile.civility and user_resident.first_name and user_resident.last_name:
        user_resident_info = {
            'complete_name':
                user_resident.profile.civility + ' ' + user_resident.first_name + ' ' + user_resident.last_name,
            'entry_date': user_resident.profileserenicia.entry_date,
        }

    # Display of documents according to the signature mode (online/handwritten)
    display_button = True
    doc_family_null = AdministrativeDocument.objects.filter(user_family__isnull=True, user_resident=user_resident)
    administrative_doc = AdministrativeDocument.objects.filter(user_resident=user_resident, user_family=user)

    if doc_family_null or administrative_doc:
        display_button = False
        button_descriptive = button_descriptive_1

        # Display doc if online signature was not used & user_family is null
        if doc_family_null:
            administrative_doc = AdministrativeDocument.objects.filter(user_resident=user_resident)
        else:
            administrative_doc = administrative_doc
    else:
        button_descriptive = f"{button_descriptive_2}"

    # Cards queryset + count the number of cards uploaded
    vital_card = Card.objects.filter(type_card='vital_card', user_resident=user_resident)
    blood_card = Card.objects.filter(type_card='blood_card', user_resident=user_resident)
    mutual_card = Card.objects.filter(type_card='mutual_card', user_resident=user_resident)
    national_card = Card.objects.filter(type_card='national_card', user_resident=user_resident)

    card_dict = {
        'vital_card': vital_card, 'blood_card': blood_card, 'mutual_card': mutual_card, 'national_card': national_card
    }

    count_card = sum(len(v) for v in card_dict.values())  # sum() -> calculates total values in dict
    if count_card != 4:
        card_downloaded = _('Card downloaded')
        total_card = f" {card_downloaded} {count_card}/4"
    else:
        all_card = _('All your residents cards have been downloaded')
        total_card = f"{all_card} {count_card}/4"

    # Cards form
    if request.method == 'POST':
        form = UploadCard(request.POST, request.FILES)

        if form.is_valid():
            instance = form.save(commit=False)
            instance.user_resident = user_resident
            data = form.cleaned_data  # Save in instance model
            Card.objects.update_or_create(
                type_card=data['type_card'], user_resident=instance.user_resident, active=True, defaults=data
            )
            messages.success(request, _(message_upload), extra_tags='success')
            return redirect('documents')

    else:
        form = UploadCard()
        user_resident_info = user_resident_info

    context = {
        'administrative_doc': administrative_doc, 'form': form, 'total_card': total_card,
        'vital_card': vital_card, 'blood_card': blood_card, 'display_button': display_button,
        'mutual_card': mutual_card, 'national_card': national_card, 'user_resident_info': user_resident_info,
        'button_descriptive': button_descriptive, 'user_resident': user_resident, 'diet_result': diet_result,
        'count_card': count_card,

        'personalized_doc': PersonalizedDocument.objects.filter(user=user, user_resident=user_resident).count(),
        'arrival_inventory': KitInventory.objects.filter(user_resident=user_resident).order_by('-creation_date'),
        'personalized_docs': PersonalizedDocument.objects.all().filter(user_resident=user_resident),
    }
    return render(request, 'app4_ehpad_base/documents/documents.html', context)


@login_required
def delete_card(request, pk):
    MESSAGE_DELETE = _('Card deleted successfully.')

    if request.method == 'POST':
        Card.objects.get(pk=pk).delete()
        messages.success(request, _(MESSAGE_DELETE), extra_tags='success')
        return redirect('documents')


# ----------------------------------------------------------------------------------------------------------------------


""" 
Function who use the api_docusign for sign personalized documents. 
Redirect message if id card or email is missing.
"""


@login_required
def sign_documents(request):
    click_here = _('click here')

    error_file = _('No documents need to be signed.')
    error_id_card = _('For more security we ask you to download your ID card to sign your documents. If not, please')
    error_email = _("A problem has occurred. Did you fill in your email correctly? If you don't, you won't be able to sign your document.")
    error_api = _("A problem has occurred. Please try again later or contact us for more information")

    try:

        # Need user id card
        if request.user.is_authenticated and Card.objects.filter(
                type_card='national_card', user_resident=User.objects.get(pk=request.user.id)
        ):
            signer_email = request.user.email
            ln_fn = f'{request.user.last_name} {request.user.first_name}'

            # Need email for sign
            if signer_email:

                if request.method == 'POST' and PersonalizedDocument.objects.filter(user=request.user.id):
                    args = Signature.get_arguments(ln_fn, signer_email)
                    args['envelope_args']['document'] = PersonalizedDocument.objects.all()

                    try:
                        post_envelope = Signature.post_envelope(args)
                        # Save envelope_id and doc_list in session
                        request.session['envelope_id'] = post_envelope['envelope_id']
                        request.session['doc_list'] = post_envelope['doc_list']

                        url_to_sign = redirect(post_envelope['redirect_url'])
                        return url_to_sign

                    except ApiException as err:
                        log_doc.error(f"Error API from sign_documents: {err}")  # API error
                        messages.error(request, _(error_api), extra_tags='error')

                        return redirect('documents')
                else:
                    messages.error(request, _(error_file), extra_tags='error')
            else:
                messages.error(request, mark_safe(
                    f"{error_email}, <a href='{settings.PUBLIC_SITE + '/profile/'}'>{click_here}.</a>"),
                               extra_tags='error')
        else:
            messages.error(request, mark_safe(
                f"{error_id_card}, <a href='{settings.PUBLIC_SITE + '/profile/'}'>{click_here}.</a>"),
                           extra_tags='error')

    except Exception as error:
        log_doc.error(f"Error generate personalized document : {error}")
        messages.error(request, _(error_api), extra_tags='error')
        return redirect('documents')

    return redirect('documents')


""" Create a administrative documents object and save it in database, with the e-signature information. """


def document_signed(request):
    message_api = _("A problem has occurred. Please try again later or contact us for more information.")
    message_success = _('Your document has been successfully signed and updated. You can read and download it whenever you want.')

    try:
        args = Signature.get_arguments(request.user.username, request.user.email)
        # .pop() remove envelope_id from session and return value
        args['envelope_id'] = request.session.pop('envelope_id')

        for document_id in request.session.pop('doc_list'):
            args['document_id'] = document_id
            doc_signed = Signature.download_document(args).get('data')
            type_document = doc_signed.split('_')[-1]

            document, is_created = AdministrativeDocument.objects.get_or_create(
                document_type=type_document.split('.')[0],
                user_resident=User.objects.get(pk=request.session['resident_id']),
                user_family=User.objects.get(pk=request.user.id),

            )
            document.envelope_id = args['envelope_id']

            with open(doc_signed, 'rb') as file:
                document.file.save(type_document, file)

            document.signer_user_id = args['envelope_args']['signer_user_id']
            document.signature_date = timezone.now()
            document.doc_id = document_id
            document.save()

    except ApiException as err:
        log_doc.error(f"Error API from document_signed: {err}")  # API error
        messages.error(request, _(message_api), extra_tags='error')
        return redirect('documents')

    messages.success(request, _(message_success), extra_tags='success')
    return redirect('documents')


# ----------------------------------------------------------------------------------------------------------------------


""" User entrance inventory form (need right access for create) + display it in inventory page. """


@login_required
def inventory(request):
    user_resident = User.objects.get(pk=request.session['resident_id'])
    user_inventory = KitInventory.objects.filter(user_resident=user_resident).order_by('-creation_date')

    context = {
        'user_inventory': user_inventory, 'user_resident': user_resident
    }

    return render(request, 'app4_ehpad_base/documents/inventory.html', context)


@login_required
def kit_inventory(request):
    created = str(_('has been created successfully'))
    message_success = str(_('Arrival inventory of'))
    message_perm = str(_('You do not have the rights to access this page'))

    if request.user.is_authenticated and request.user.has_perm('app0_access.view_care'):
        user_resident = User.objects.get(pk=request.session['resident_id'])

        if request.method == 'POST':
            kit_form = KitInventoryForm(request.POST)

            if kit_form.is_valid():
                instance = kit_form.save(commit=False)
                instance.user_resident = user_resident
                instance.nurses = request.user
                instance.creation_date = timezone.now()
                kit_form.save()

                messages.success(request,
                                 f"{message_success} {user_resident.last_name} {user_resident.first_name} {created}",
                                 extra_tags='success'
                                 )
                return redirect('inventory')

            else:
                log_doc.error(kit_form.errors)

        else:
            kit_form = KitInventoryForm()

        context = {
            'kit_form': kit_form, 'user_resident': user_resident,
            'user_inventory': KitInventory.objects.filter(user_resident=user_resident).exists()
        }
        return render(request, 'app4_ehpad_base/documents/create_inventory.html', context)

    else:
        messages.error(request, _(message_perm), extra_tags='error')
        return redirect('/inventory/')


def laundry_management(request):
    try:
        request.session.pop('resident_id')
    except KeyError:
        pass
    laundry_washed = KitInventory.objects.all().filter(laundry_washed='washed by residence')
    laundry_labeled = KitInventory.objects.all().filter(laundry_labeled='labeled by residence')

    if request.user.is_authenticated and request.user.has_perm('app0_access.view_care'):
        laundry_washed = laundry_washed
        laundry_labeled = laundry_labeled

    context = {
        'laundry_washed': laundry_washed, 'laundry_labeled': laundry_labeled,
    }

    return render(request, 'app4_ehpad_base/documents/laundry_management.html', context)


# ----------------------------------------------------------------------------------------------------------------------


""" Form for user family can add resident information. """


def resident_form(request):
    message_success = _('Information has been added')
    user_resident = User.objects.get(pk=request.session['resident_id'])

    if request.method == 'POST':

        u_resident = ResidentForm(request.POST, instance=user_resident)
        p_resident = ProfileResidentForm(request.POST, instance=user_resident.profile)
        pf_resident = ProfileSereniciaForm(request.POST, instance=user_resident.profileserenicia)

        # Resident profile (name, birth date ect ...)
        if pf_resident.is_valid() and u_resident.is_valid() and p_resident.is_valid():
            pf_resident.save() and u_resident.save() and p_resident.save()

            messages.success(request, _(message_success), extra_tags='success')
            return redirect('documents')

        else:
            log_doc.debug(pf_resident.errors, u_resident.errors, p_resident.errors)

    else:
        diet_form = DietForm()

        u_resident = ResidentForm(instance=user_resident)
        p_resident = ProfileResidentForm(instance=user_resident.profile)
        pf_resident = ProfileSereniciaForm(instance=user_resident.profileserenicia)

    context = {
        'user_resident': user_resident, 'pf_resident': pf_resident,
        'u_resident': u_resident, 'p_resident': p_resident,
    }

    return render(request, 'app4_ehpad_base/documents/resident_form.html', context)


def diet(request):
    message_success = _('Information has been added')
    user_resident = User.objects.get(pk=request.session['resident_id'])
    diet_ = Diet.objects.filter(user_resident=user_resident)

    if request.method == 'POST':
        diet_form = DietForm(request.POST)

        if diet_form.is_valid():

            instance = diet_form.save(False)
            instance.user_resident = user_resident

            data = diet_form.cleaned_data

            if diet_:
                diet_.update(
                    type_diet=data['type_diet'], food_option=data['food_option'], allergies=data['allergies'],
                )

            else:
                diet_ = Diet(
                    type_diet=data['type_diet'], food_option=data['food_option'],
                    allergies=data['allergies'], user_resident=instance.user_resident,
                )
                diet_.save()

            messages.success(request, _(message_success), extra_tags='success')
            return redirect('documents')

    else:
        diet_form = DietForm()

    return render(request, 'app4_ehpad_base/documents/diet.html', {'diet_form': diet_form})

# ----------------------------------------------------------------------------------------------------------------------


def progress_bar(request):
    """ Progress bar of data recorded in serenicia.For documents if the online signature is used
    each doc is x2(10 * 2 = 20%), if not 1 doc = 20 because the number of doc per family is random """

    suffix = str('%')
    click_here = str(_('click here'))
    prefix = str(_('File completed at'))

    user = User.objects.get(pk=request.user.id)
    user_resident = User.objects.get(pk=request.session['resident_id'])

    # Card 20%
    card = Card.objects.filter(user_resident=user_resident).count()
    percent = (card * int(5))
    if card != 4:
        info_card = _('Some cards about the resident are missing')
        messages.info(request, mark_safe(
            f"{info_card}, <a href='{settings.PUBLIC_SITE + '/documents/'}'>{click_here}.</a>"), extra_tags='info')

    # Document 40%
    document = AdministrativeDocument.objects.filter(user_resident=user_resident, user_family=user).count()
    if document:
        percent = percent + (document * int(4))
    elif AdministrativeDocument.objects.filter(user_family__isnull=True, user_resident=user_resident):
        percent = percent + int(40)
    else:
        info_document = _('It is important to sign your documents')
        messages.info(request, mark_safe(
            f"{info_document}, <a href='{settings.PUBLIC_SITE + '/documents/'}'>{click_here}.</a>"), extra_tags='info')

    # Family 10%
    # _user_family_ = {
    #     'last_name': user.last_name, 'first_name': user.first_name, 'email': user.email,
    #     'birth_date': user.profileserenicia.birth_date, 'civility': user.profile.civility,
    #     'phone_number': user.profile.phone_number,
    # }
    #
    # card_user_family = Card.objects.filter(user_resident=user)
    # if card_user_family.exists():
    #     _user_family_['card_user_family'] = card_user_family
    #
    # user_family_ = {
    #     key: value for key, value in _user_family_.items()
    #     if value is not None and (
    #             not isinstance(value, str) or value.strip()
    #     )
    # }
    # percent_family = int((len(user_family_) * float(1.4285714285714286)))

    # if percent_family != 10:
    #     info_family = _('Information about you was not recorded')
    #     messages.info(request, mark_safe(
    #         f"{info_family}, <a href='{settings.PUBLIC_SITE + '/profile/'}'>{click_here}.</a>"), extra_tags='info')

    # Resident 20%
    _user_resident_ = {
        'last_name': user_resident.last_name, 'first_name': user_resident.first_name,
        'civility': user_resident.profile.civility, 'birth_date': user_resident.profileserenicia.birth_date,
        'birth_city': user_resident.profileserenicia.birth_city,
    }
    user_resident_ = {
        key: value for key, value in _user_resident_.items()
        if value is not None and (
                not isinstance(value, str) or value.strip()
        )
    }
    percent_resident = int((len(user_resident_) * int(4)))

    if percent_resident != 20:
        info_resident = _('Some information about your resident is missing')
        messages.info(request, mark_safe(
            f"{info_resident}, <a href='{settings.PUBLIC_SITE + '/profile/'}'>{click_here}.</a>"), extra_tags='info')

    # Video 20%
    if len(glob.glob(settings.MEDIA_ROOT + "/videos_users/" + request.user.profileserenicia.folder + "/*.mp4")) != 0:
        video = settings.MEDIA_URL + "videos_users/" + request.user.profileserenicia.folder + "/" + request.user.profileserenicia.folder + ".mp4"
        if video:
            percent += 20
    else:
        info_video = _('To create your video')
        create_video = _('and Create my video')
        messages.info(request, mark_safe(
            f"{info_video}, <a href='{settings.PUBLIC_SITE + '/profile/'}'>{click_here}</a> {create_video}."),
                      extra_tags='info')

    # Passphrase 10%
    # if user.profileserenicia.passphrase:
    #     percent += 10
    # else:
    #     info_passphrase = _('To create your passphrase')
    #     messages.info(request, mark_safe(
    #         f"{info_passphrase}, <a href='{settings.PUBLIC_SITE + '/passphrase/'}'>{click_here}.</a>"),
    #                   extra_tags='info')

    # World 10%
    # if user.profileserenicia.word_played:
    #     percent += 10
    # else:
    #     info_word = _('To create your word')
    #     messages.info(request, mark_safe(
    #         f"{info_word}, <a href='{settings.PUBLIC_SITE + '/record/'}'>{click_here}.</a>"), extra_tags='info')

    percent_total = int(percent) + percent_resident
    results = f"{prefix} {percent_total} {suffix}"

    return {'percent_total': percent_total, 'results': results}
