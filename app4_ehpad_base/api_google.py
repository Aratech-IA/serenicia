import base64
import time
from google.oauth2 import service_account
import re
from googleapiclient.discovery import build
from googleapiclient import errors
import json
from app4_ehpad_base.models import ProfileSerenicia
from django.conf import settings
from app1_base.log import Logger
import logging
from google.auth.exceptions import RefreshError

if 'log_calendar' not in globals():
    log_calendar = Logger('calendar', level=logging.INFO).run()

# >>>>>>>>>> Fist part is to manage service account with google <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<


def create_service_account(service, project_id, name, display_name):
    """Creates a service account."""
    my_service_account = service.projects().serviceAccounts().create(
        name='projects/' + project_id,
        body={
            'accountId': name,
            'serviceAccount': {
                'displayName': display_name
            }
        }).execute()
    return my_service_account


def enable_service_account(service, email_id):
    """Enables a service account."""
    service.projects().serviceAccounts().enable(name='projects/-/serviceAccounts/' + email_id).execute()


def delete_service_account(service, email_id):
    """Deletes a service account."""
    service.projects().serviceAccounts().delete(name='projects/-/serviceAccounts/' + email_id).execute()


def create_key(service, email_id):
    """Creates a key for a service account."""
    key = service.projects().serviceAccounts().keys().create(
        name='projects/-/serviceAccounts/' + email_id, body={'privateKeyType': 'TYPE_GOOGLE_CREDENTIALS_FILE'}
        ).execute()
    decoded = base64.b64decode(key['privateKeyData'])
    token = json.loads(decoded)
    return token


def has_key(service, email_id):
    """Checks if the service account email given has its own Json key or not, returns key"""
    keys = service.projects().serviceAccounts().keys().list(name='projects/-/serviceAccounts/' + email_id).execute()
    return keys


def delete_key(service, full_key_name):
    """Deletes a service account key."""
    service.projects().serviceAccounts().keys().delete(name=full_key_name).execute()


def list_service_accounts_emails(service, project_id):
    """Lists all service accounts for the current project."""
    emails_list = []
    request = service.projects().serviceAccounts().list(name='projects/' + project_id)
    while True:
        response = request.execute()
        email_list = response['accounts']
        for email in email_list:
            emails_list.append(email['email'])
        request = service.projects().serviceAccounts().list_next(previous_request=request, previous_response=response)
        if not request:
            break
    return {mail.split('@')[0]: mail for mail in emails_list}


# noinspection PyUnresolvedReferences,PyUnboundLocalVariable
def check_service_account():
    for key in settings.LIST_PROJECT:
        project = key['project_id']

        """Attribute project to service accounts"""
        # noinspection PyUnresolvedReferences
        nb_use = len(ProfileSerenicia.objects.filter(gcp_project=project, user__groups__permissions__codename='view_resident'))
        q = ProfileSerenicia.objects.filter(gcp_project='undefined', user__groups__permissions__codename='view_resident')[:70 - nb_use]
        ProfileSerenicia.objects.filter(id__in=q).update(gcp_project=project)

        """Create credential for google service access"""
        scopes = ['https://www.googleapis.com/auth/cloud-platform']
        credentials = service_account.Credentials.from_service_account_info(key, scopes=scopes)
        service = build('iam', 'v1', credentials=credentials)

        sa_email_dict = list_service_accounts_emails(service, project)

        """Create service accounts, if needed update profileserenicia"""
        users_to_set = ProfileSerenicia.objects.filter(service_account_file='{}',
                                                       user__groups__permissions__codename='view_resident',
                                                       gcp_project=project)
        for pj in users_to_set:
            # Creating a service account per user_resident who doesn't have one yet
            try:
                mail_id = re.sub('[^A-Za-z0-9]+', '', pj.user.username)
                sa = create_service_account(service, project, mail_id[:30], pj.user.first_name+" "+pj.user.last_name)
                pj.sa_email = sa['email']
                log_calendar.info(f'create service account {sa["email"]}')
                time.sleep(1)
                token = create_key(service, sa['email'])
                pj.service_account_file = token
                log_calendar.info(f'create key')
                time.sleep(1)
                enable_service_account(service, sa['email'])
                pj.has_active_service_account = True
                pj.save()
                log_calendar.info(f'save account')
            except errors.HttpError as e:
                # check if service account already exist
                if mail_id in sa_email_dict:
                    try:
                        log_calendar.info(f'user  {sa_email_dict[mail_id]} already exist')
                        token_name = has_key(service, sa_email_dict[mail_id])['keys']
                        for k in token_name:
                            delete_key(service, k['name'])
                        token = create_key(service, sa_email_dict[mail_id])
                        pj.service_account_file = token
                        log_calendar.info(f'create new  key')
                        time.sleep(1)
                        enable_service_account(service, sa['email'])
                        pj.has_active_service_account = True
                        pj.save()
                        log_calendar.info(f'save already existing account')
                    except errors.HttpError as e:
                        log_calendar.info(f'error when trying to recreate key --> {e}')
                else:
                    log_calendar.info(f'error on service account --> {e}')
                pass


def clean_key():  # function not really usefull -  only for construction and test
    ProfileSerenicia.objects.filter(user__groups__permissions__codename='view_resident').update(service_account_file='{}')


# >>>>>>>>>> Second part is to manage calendar of each service account <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<


def add_rule(access, cal_id):
    """ This acl rule is needed to have a public access on the calendar """
    rule = {
        'scope': {
            'type': 'default',
            'value': 'default',
        },
        'role': 'reader'
        }
    access.acl().insert(calendarId=cal_id, body=rule).execute()


def check_calendar(has_service_account=True, has_calendar=False):
    users_calendar = ProfileSerenicia.objects.filter(user__groups__permissions__codename='view_resident',
                                                     has_active_subcalendar=has_calendar,
                                                     has_active_service_account=has_service_account)
    scopes = ['https://www.googleapis.com/auth/calendar']
    for pj in users_calendar:
        try:
            key = pj.service_account_file
            credentials = service_account.Credentials.from_service_account_info(key, scopes=scopes)
            access = build('calendar', 'v3', credentials=credentials)
            calendar = access.calendarList().list().execute()
            log_calendar.info(f'checking if calendar exists --> {calendar["items"]}')
            if not calendar['items']:
                body = {'summary': pj.user.first_name+' '+pj.user.last_name, 'timeZone': settings.TIME_ZONE}
                created_calendar = access.calendars().insert(body=body).execute()
                log_calendar.info(f'calendar create for {pj.user}')
            else:
                created_calendar = calendar['items'][0]
                log_calendar.info(f'calendar find for {pj.user}')
            pj.cal_id = created_calendar['id']
            add_rule(access, pj.cal_id)
            log_calendar.info(f'add public acl for the calendar --> {pj.cal_id}')
            pj.has_active_subcalendar = True
            pj.save()
            log_calendar.info(f'calendar saved for {pj.user}')
        except (errors.HttpError, RefreshError) as e:
            log_calendar.info(f'error on service account --> {e} for {pj.user} ')
            pass


# >>>>>>>>>>>>>>>>>>>>>>>>>>>>> Third part is to manage event in the google calendar <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<

def add_event(access, cal_id, event):
    event = access.events().insert(calendarId=cal_id, body=event).execute()
    return event


def update_event(access, cal_id, event_id, event):
    event = access.events().update(calendarId=cal_id, eventId=event_id, body=event).execute()
    return event


def delete_event(access, cal_id, event_id):
    access.events().delete(calendarId=cal_id, eventId=event_id).execute()
