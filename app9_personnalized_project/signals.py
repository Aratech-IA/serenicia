from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.dispatch import receiver
from django.db.models.signals import post_save, pre_delete
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from app3_messaging.mails import sendnotif
from app3_messaging.notifs import constance_martin
from app9_personnalized_project.models import Appointment


def get_formatted_date_day_nb_month(date):
    # similaire à strptime('%A %-d %B') avec traduction
    day = {0: _('Monday'), 1: _('Tuesday'), 2: _('Wednesday'), 3: _('Thursday'), 4: _('Friday'), 5: _('Saturday'),
           6: _('Sunday')}
    month = {1: _('January'), 2: _('February'), 3: _('March'), 4: _('April'), 5: _('May'), 6: _('June'), 7: _('July'),
             8: _('August'), 9: _('September'), 10: _('October'), 11: _('November'), 12: _('December')}
    return f'{day[date.weekday()]} {date.day} {month[date.month]}'


def send_mail(email: list, mail_content: dict, template: str):
    args = {'subject': mail_content['subject'], 'templatename': template, 'recipient_emails': email,
            'flexcontent': mail_content['message'], 'link_redirect': [], 'nomsymbdjango': ['First Name'],
            'sender': constance_martin}
    if template == 'notif_appointment_app8_sp':
        args['link_redirect'].append(reverse('support project appointments'))
    sendnotif(**args)


def get_mail_content_sp(recipient, appointment):
    resident_full_name = appointment.planning_event.participants.get(
        user__groups__permissions__codename='view_residentehpad').user.get_full_name()
    rec_type = {'owner': {'subject': _('Appointment saved'),
                          'message': [_('The next appointment has been saved : personalized support project of'),
                                      resident_full_name]},
                'guest': {'subject': _('Waiting for confirmation'),
                          'message': [_('You have been invited to participate in the personalized support project of'),
                                      resident_full_name]},
                'sp_creator_new': {'subject': _('New appointment'),
                                   'message': [_('You have a new support project appointment for'),
                                               resident_full_name]},
                'sp_creator_update': {'subject': _('Modified appointment'),
                                      'message': [_('A new person has been added to the next appointment of'),
                                                  resident_full_name]}}
    date_str = get_formatted_date_day_nb_month(appointment.planning_event.start)
    return {'message': [rec_type[recipient]['message'], date_str,
                        appointment.planning_event.start.strftime('%Hh%M'),
                        appointment.planning_event.end.strftime('%Hh%M')],
            'subject': rec_type[recipient]['subject']}


def get_mail_content_demo(recipient, appointment):
    name, tel, mail, = _('Name'), _('Phone number'), _('Mail')
    date_str = f'{get_formatted_date_day_nb_month(appointment.planning_event.start)} {appointment.planning_event.start.strftime("%Hh%M")} {appointment.planning_event.end.strftime("%Hh%M")}'
    rec_type = {'prospect': {'message': [_('Your demonstration request has been registered for the following date'),
                                         date_str,
                                         _('Our teams will contact you shortly with the contact details you provided')],
                             'subject': _('Appointment saved')},
                'contactdemo': {'message': [_('A new demonstration request has been registered'),
                                            date_str,
                                            f'{name} : {appointment.profileserenicia.user.get_full_name()}, {tel} : {appointment.profileserenicia.user.profile.phone_number}, {mail} : {appointment.profileserenicia.user.email}'],
                                'subject': _('New demonstration appointment')}}
    return rec_type[recipient]


def send_confirmation_mail_support_project(appointment, template):
    send_to = {}
    if appointment.owner:
        send_to['family'] = 'owner'
        send_to['sp_creator'] = 'sp_creator_new'
    elif not appointment.rejected:
        send_to['family'] = 'guest'
        send_to['sp_creator'] = 'sp_creator_update'
    if appointment.profileserenicia.user.email and send_to.get('family'):
        send_mail(email=[appointment.profileserenicia.user.email],
                  mail_content=get_mail_content_sp(send_to['family'], appointment),
                  template=template)
    if appointment.planning_event.event.organizer.user.email and send_to.get('sp_creator'):
        send_mail(email=[appointment.planning_event.event.organizer.user.email],
                  mail_content=get_mail_content_sp(send_to['sp_creator'], appointment),
                  template=template)


def send_confirmation_mail_demonstration(appointment, template):
    send_mail(email=[appointment.profileserenicia.user.email],
              mail_content=get_mail_content_demo('prospect', appointment),
              template=template)
    send_mail(email=[user.email for user in User.objects.filter(groups__permissions__codename='view_contactdemo',
                                                                email__isnull=False)],
              mail_content=get_mail_content_demo('contactdemo', appointment), template=template)


@receiver(post_save, sender=Appointment)
def sending_participation_email_support_project(instance, created, **kwargs):
    if created:
        if instance.planning_event.event.type == 'support project':
            send_confirmation_mail_support_project(appointment=instance, template='notif_appointment_app8_sp')
        elif instance.planning_event.event.type == 'demonstration' and instance.owner:
            send_confirmation_mail_demonstration(appointment=instance, template='notif_appointment_app999_demo')


@receiver(pre_delete, sender=Appointment)
def sending_cancellation_email_support_project(instance, **kwargs):
    if instance.profileserenicia.user.email:
        template = 'notif_appointment_app8_sp'
        recipients = [instance.profileserenicia.user.email]
        if instance.planning_event.event.organizer.user.email:
            recipients.append(instance.planning_event.event.organizer.user.email)
        try:
            full_name = instance.planning_event.participants.get(
                       user__groups__permissions__codename='view_residentehpad').user.get_full_name()
        except ObjectDoesNotExist:
            full_name = ''
        message = [_('One of your appointments has been canceled: personalized support project of'),
                   full_name, get_formatted_date_day_nb_month(instance.planning_event.start),
                   instance.planning_event.start.strftime('%Hh%M'), instance.planning_event.end.strftime('%Hh%M')]
        send_mail(email=recipients, mail_content={'message': message, 'subject': _('Appointment canceled')},
                  template=template)
