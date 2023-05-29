import sys
import os
import json
import requests
import time
import logging


# ------------------------------------------------------------------------------
# Because this script have to be run in a separate process from manage.py
# you need to set up a Django environnement to use the Class defined in
# the Django models. It is necesssary to interact witht the Django database
# ------------------------------------------------------------------------------
# to get the projet.settings it is necessary to add the parent directory
# to the python path
try:
    from app1_base.models import Telegram, UpdateId, Profile, Alert
except ModuleNotFoundError:
    try:
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    except NameError:
        sys.path.append(os.path.abspath('..'))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "projet.settings.settings")
    import django
    django.setup()
    from app1_base.models import Telegram, UpdateId, Profile, Alert

from django.utils.translation import gettext as _
from django.utils import translation
from django.conf import settings
from app1_base.log import Logger

if 'log_telegram' not in globals():
    log_telegram = Logger('telegram', level=logging.ERROR).run()

botid = settings.TELEGRAM_TOKEN
get_update_url = f"https://api.telegram.org/{botid}/getUpdates"
send_message_url = f"https://api.telegram.org/{botid}/sendMessage"
send_photo_url = f"https://api.telegram.org/{botid}/sendPhoto"


def send_chat_photo(chatid, photo):
    try:
        files = photo
        data = {'chat_id': chatid}
        requests.post(send_photo_url, data=data, files=files)
    except Exception as repex:
        log_telegram.warning(f'Error while send Message: {repex}')


def send_chat_message(chatid, message):
    try:
        params = [('chat_id', chatid), ('text', message)]
        requests.get(send_message_url, params)
    except Exception as repex:
        log_telegram.warning(('Error while send Message: {}'.format(repex)))

# ICI Controler que le userid plus bas existe dans la DB Protecia et stocker les usersinfos dans la
# BDD d'Protecia (l'object JSON de newuser par exemple)
# 1 - il peut y avoir N   telegram user -> 1  Protecia User
# 2 - un user Telegram peut etre present pour plusieurs Protecia User
# pour notifier potentiellement plusieurs personnes


def command_register(username, chatid, first_name, last_name, token):
    try:
        log_telegram.warning(f"REGISTERING user  {first_name} {last_name} as user ID={chatid}")
        profile = Profile.objects.get(telegram_token=token)  # exception if invalid token
        translation.activate(profile.language)
        if Telegram.objects.filter(profile=profile, chat_id_char=chatid).exists():
            send_chat_message(chatid, username)
        else:
            Telegram(profile=profile, chat_id_char=chatid, name=first_name + ' ' + last_name).save()
            send_chat_message(chatid, _('Ok you are registered') + ' ' + '{}'.format(first_name) + '.')
        return True
    except Profile.DoesNotExist as ex:
        log_telegram.warning(f"Register is not for this server : {ex}")
        return False


def consumme_message(obj):
    ofrom = obj['from']
    first_name = ofrom.get('first_name', "[first name]")
    last_name = ofrom.get('last_name', "[last name]")
    username = ofrom.get('username', "[username]")
    userid = obj['from']['id']
    language = obj['from']['language_code']
    message_id = obj['message_id']
    chat_id = obj['chat']['id']
    log_telegram.debug(f"chat_id is {type(chat_id) }")
    translation.activate(language)

    if 'text' in obj:
        text = obj['text']
    else:
        text = ''

    # first case message is generic all the servers can process the message and go forward in the queue
    if text[0:5] == "/help":

        send_chat_message(chat_id, f'{first_name},' + _("Commands are:") + "\n /register" + _("[Protecia UserID]") +
                          " =>" + _("Register your Protecia Account") + "\n")
        return True
    if text[0:6] == "/start":
        send_chat_message(chat_id,
                          _("Hi") + " {}".format(first_name) +
                          ", \n" +
                          _("I am Protecia Bot. You shall first register your "
                            "Protecia user ID in order to receive  Protecia notifications.") +
                          "\n\n" +
                          _("Type") + " " + "/help" + " " +
                          _("to start."))
        send_chat_message(chat_id,
                          "(" +
                          _("For your information, your Telegram user id is: ") +
                          "{}".format(userid) +
                          ")")
        return True

    # second case, register message the client have to be registered on the right server
    if text[0:9] == "/register":
        return command_register(username, chat_id, first_name, last_name, text[10:])

    # third case action from a registered user
    # use language code if no protecia profile
    if text[0:4] == "stop" or text[0:4] == "Stop":
        telegram_user = Telegram.objects.filter(chat_id_char=chat_id).first()
        if telegram_user:
            profile = telegram_user.profile
            translation.activate(profile.language)
            log_telegram.info(f"Message from  [{first_name} {last_name}({username})] {text}")
            alert = Alert.objects.filter(client=profile.client)
            is_alert = not any([i.active for i in alert])
            if is_alert:
                send_chat_message(chat_id,
                                  "{}".format(first_name) +
                                  ", " +
                                  _("There isn't any active alarm. The place is quiet."))
            else:
                for a in alert:
                    a.active = False
                    a.save()
                send_chat_message(chat_id,
                                  "{}".format(first_name) + ", " +
                                  _("Alarm is stop."))
            return True
        else:
            send_chat_message(chat_id,
                              "{}".format(first_name) + " , " +
                              _("I don't understand this command , type") +
                              " /help")
            return False

    # Unknown Command
    send_chat_message(chat_id,
                      "{}".format(first_name) + " , " +
                      _("I don't understand this command , type") +
                      " /help")
    return True


def get_updates(msg_id):
    url = '{}?offset={}'.format(get_update_url, msg_id)
    try:
        return requests.get(url)
    except requests.exceptions.ConnectionError:
        log_telegram.warning('Exception calling URL {}'.format(url))
        return False


def main(freq):
    log_telegram.warning('Enter main')
    try:
        update_id = UpdateId.objects.get()
    except UpdateId.DoesNotExist:
        UpdateId(id_number=0).save()
        update_id = UpdateId.objects.get()
        pass
    while True:
        log_telegram.warning('checking messages')
        r = get_updates(update_id.id_number)
        if r and r.status_code == 200:
            try:
                obj = json.loads(r.text)
                if obj['ok']:
                    for o in obj['result']:
                        try:
                            if 'message' in o:
                                log_telegram.info(str(o['update_id']))
                                update_id.id_number = o['update_id']
                                update_id.save()
                                if consumme_message(o['message']):
                                    update_id.id_number += 1
                                    get_updates(update_id.id_number)
                                    log_telegram.info(f'consume message: {o["message"]}')
                                else:
                                    if update_id.already_call:
                                        update_id.id_number += 1
                                        get_updates(update_id.id_number)
                                    else:
                                        update_id.already_call = True
                                        update_id.save()
                                        break
                        except AttributeError as e:
                            log_telegram.warning('Error while parsing result {}'.format(e))
                            pass
            except AttributeError as rqe:
                log_telegram.warning('Object is not a Json object: {}'.format(rqe))
        time.sleep(freq)

# start the process


if __name__ == '__main__':
    main(2)
