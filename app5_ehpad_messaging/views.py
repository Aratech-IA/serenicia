from datetime import timedelta

from django.contrib.auth.models import User
from django.shortcuts import render, redirect
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.decorators import login_required
from django.conf import settings as param

from app3_messaging.models import IntraEmail, IntraEmailAttachment, Intermediate, Conversation
from app1_base.models import ProfileSecurity
from app3_messaging.forms import IntraEmailAttachmentForm
from app5_ehpad_messaging.utils import create_ref
from app3_messaging.textprocess import htmltotext
from app1_base.log import Logger
from app15_calendar.models import Event, PlanningEvent

# The model used for this app depend on the domain Protecia or Serenicia, we need to get the correct model.
if "protecia" in param.DOMAIN.lower():
    model_linked = ProfileSecurity
else:
    from app4_ehpad_base.models import ProfileSerenicia

    model_linked = ProfileSerenicia


@login_required
def internal_emailing_family(request):
    connected_user = ''
    if request.user.is_authenticated:
        connected_user = User.objects.get(pk=request.user.id)
    try:
        resident = User.objects.select_related('profileserenicia').get(pk=request.session['resident_id'])
    except:
        resident = False
    sent = False
    convo_id = False
    if request.method == 'POST':
        if "contact_ref" in request.POST:
            form = IntraEmailAttachmentForm()
            data = dict(request.POST.items())
            ref_type = data["contact_ref"]
            # ALEXIS-------------------------------------
            if ref_type == 'view_family':
                refs = []
                family_list = User.objects.filter(
                    profileserenicia__user_list__user=request.session['resident_id']).exclude(
                    id=request.user.id)
                for user in family_list:
                    if user.has_perm('app0_access.view_family'):
                        refs.append(user)
            elif ref_type == 'view_one_family':
                refs = [User.objects.get(id=request.POST.get('family_id'))]
            else:
                refs = create_ref(resident, ref_type)
            # --------------------------------------------
            context = {"tinymce_key": param.TINYMCE_KEY, "user": connected_user, "sent": sent, "resident": resident,
                       "convo_id": convo_id, "form": form, "refs": refs}
            return render(request, 'app5_ehpad_messaging/internal_emailing_family.html', context)
        if "messagefamille" in request.POST:
            form = IntraEmailAttachmentForm(request.POST, request.FILES)
            data = dict(request.POST.items())
            recipients_id = []
            try:
                recipients_id = request.POST.getlist("recipients[]")
            except KeyError:
                pass
            subject = data["subject"]
            content = data["content"]

            convo = Conversation()
            convo.save()
            createemail = IntraEmail(subject=subject, content=content, message_conversation=convo,
                                     content_text=htmltotext(content), date_sent=timezone.now(), is_support=True)
            createemail.save()

            if form.is_valid():
                for file in request.FILES.getlist('attachment'):
                    add_attachment = IntraEmailAttachment(attachment=file, intraemail=createemail)
                    name = add_attachment.attachment.url.split('/')[-1].split('.')[0]
                    add_attachment.name = name
                    add_attachment.save()

            Intermediate(message=createemail, recipient=connected_user, user_type='sender').save()

            [Intermediate(message=createemail, recipient=User.objects.get(id=rec_id),
                          user_type='default').save() for rec_id in recipients_id if
             int(rec_id) != int(connected_user.id)]

            [Intermediate(message=createemail, recipient=User.objects.get(username=user),
                          user_type='CC').save()
             for user in create_ref(resident, "view_family", recipients_id) if user != connected_user]

            sent = True
            return redirect("personal page")


def on_day(date, day):
    next_day = date + timedelta(days=(day - date.isoweekday() + 7) % 7)
    start = next_day.replace(hour=8, minute=00, second=00, microsecond=00)
    end = next_day.replace(hour=18, minute=00, second=00, microsecond=00)
    return start, end


def add_date_doctor(request, doctor, day):
    date = timezone.now()
    appointement_start, appointement_end = on_day(date, day)
    doctor = User.objects.get(pk=doctor)
    residents = doctor.profileserenicia.user_list.filter(user__groups__permissions__codename="view_residentehpad")
    residents_final = []
    for resident in residents:
        residents_final.append(resident.user.profileserenicia)
    event, was_event_created = Event.objects.get_or_create(is_visit=True, organizer=doctor.profileserenicia)
    if not event.type:
        event.type = "visit"
    p_event, was_created = PlanningEvent.objects.get_or_create(event=event, start=appointement_start,
                                                               end=appointement_end)
    if was_created:
        p_event.participants.add(*residents_final)

    context = {}
    return render(request, 'app5_ehpad_messaging/date_confirmation.html', context)
