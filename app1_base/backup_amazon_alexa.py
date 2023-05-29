# -*- coding: utf-8 -*-

# This sample demonstrates handling intents from an Alexa skill using the Alexa Skills Kit SDK for Python.
# Please visit https://alexa.design/cookbook for additional examples on implementing slots, dialog management,
# session persistence, api calls, and more.
# This sample is built using the handler classes approach in skill builder.
import logging
import ask_sdk_core.utils as ask_utils

from ask_sdk_core.skill_builder import CustomSkillBuilder, SkillBuilder
from ask_sdk_core.api_client import DefaultApiClient
from ask_sdk_core.dispatch_components import AbstractRequestHandler, AbstractExceptionHandler
from ask_sdk_core.handler_input import HandlerInput

from ask_sdk_model.services.reminder_management import (
    Trigger, TriggerType, AlertInfo, SpokenInfo, SpokenText, PushNotification, PushNotificationStatus, ReminderRequest,
    Recurrence, RecurrenceFreq, Reminder, Status)
from ask_sdk_model.services.reminder_management.get_reminders_response import GetRemindersResponse  # test

from ask_sdk_model.er.dynamic import UpdateBehavior, EntityListItem, Entity, EntityValueAndSynonyms
from ask_sdk_model.dialog import DynamicEntitiesDirective
from ask_sdk_model import Response
from ask_sdk_model.services.service_exception import ServiceException
from ask_sdk_model.interfaces.connections import SendRequestDirective
from ask_sdk_model.ui import SimpleCard, AskForPermissionsConsentCard
import time, datetime
import pytz
import requests
import json
import typing

if typing.TYPE_CHECKING:
    from ask_sdk_core.handler_input import HandlerInput
    from ask_sdk_model import Response

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


# Function to send Json Request to Serenicia server, just need send data Json as param
def send_request_to_serenicia_server(data):
    try:
        r = requests.post("https://dev.serenicia.fr/alexa", data=data,
                          timeout=40)  # https://dev.serenicia.fr/alexa       https://0.0.0.0/alexa
        logger.warning('send json : {}'.format(r.status_code))
        return r.json()
    except (requests.exceptions.ConnectionError, requests.Timeout):
        logger.warning('Can not find the remote server')
        time.sleep(5)
        pass


# function to set reminder when needed.
def set_reminder(handler_input, time, freq, sentence, text):
    request_envelope = handler_input.request_envelope
    response_builder = handler_input.response_builder
    reminder_service = handler_input.service_client_factory.get_reminder_management_service()

    now = datetime.datetime.now(pytz.timezone("Europe/Paris"))
    one_min_from_now = now + datetime.timedelta(minutes=+5)
    notification_time = one_min_from_now.strftime("%Y-%m-%dT%H:%M:%S")
    logger.warning(notification_time)

    if not (
            request_envelope.context.system.user.permissions and request_envelope.context.system.user.permissions.consent_token):
        return "L'option des rappels est Désactivé. Merci d'autoriser les rappels dans l'application Alexa de votre smartphone, dans les paramètres de la skill bonjour Serenicia."

    trigger = Trigger(object_type=TriggerType.SCHEDULED_ABSOLUTE,
                      scheduled_time=notification_time,
                      time_zone_id="Europe/Paris",
                      recurrence=Recurrence(recurrence_rules=freq))

    text = SpokenText(locale='fr-FR',
                      ssml="<speak> <audio src=\"soundbank://soundlibrary/ui/gameshow/amzn_ui_sfx_gameshow_positive_response_02\"/>" + sentence + "</speak>",
                      text=text)
    alert_info = AlertInfo(SpokenInfo([text]))
    push_notification = PushNotification(PushNotificationStatus.ENABLED)
    reminder_request = ReminderRequest(notification_time, trigger, alert_info, push_notification)

    try:
        reminder_response = reminder_service.create_reminder(reminder_request)
        logger.info("Reminder Created: {}".format(reminder_response))
    except ServiceException as e:
        logger.info("Exception encountered: {}".format(e.body))
        return response_builder.speak("Le rappelà échoué.").response

    return "<audio src=\"soundbank://soundlibrary/ui/gameshow/amzn_ui_sfx_gameshow_neutral_response_03\"/>Votre rappel vient d'être ajouté !"


# def that checks if reminder already exists in reminders of alexa
def check_if_reminder_exist(handler_input, text):
    reminder_service = handler_input.service_client_factory.get_reminder_management_service()
    list_reminders = reminder_service.get_reminders()
    for i in range(len(list_reminders.alerts)):
        logger.warning(list_reminders.alerts[i].alert_info.spoken_info.content)
        logger.info(list_reminders.alerts[i].trigger.scheduled_time)
        logger.error(list_reminders.alerts[i].push_notification.status)
        if list_reminders.alerts[i].alert_info.spoken_info.content[0].text == text and list_reminders.alerts[
            i].status == Status.COMPLETED:
            list_reminders.alerts[i].status = Status.ON
            logger.info(list_reminders.alerts[i].status)
            return False
    return True


# def that gives me the id of the slots i need
def get_id_of_contact(var):
    for i in range(len(var.resolutions.resolutions_per_authority)):
        if var.resolutions.resolutions_per_authority[i].values != None:
            answer = var.resolutions.resolutions_per_authority[i].values[0].value.id
    return answer


class LaunchRequestHandler(AbstractRequestHandler):
    """Handler for Skill Launch."""

    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool

        return ask_utils.is_request_type("LaunchRequest")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        # speak_output = "<say-as interpret-as=\"interjection\"> Bonjour </say-as>, quel service Serenicia voulez vous utiliser ?"
        speak_output = "<amazon:emotion name=\"excited\" intensity=\"high\">Bienvenue chez Serenicia, que puis je faire pour vous ?</amazon:emotion>"
        # speak_output += "<voice name=\"Celine\">Bienvenue chez Serenicia, que puis je faire pour vous ?</voice>."
        # speak_output += "<voice name=\"Lea\">Bienvenue chez Serenicia, que puis je faire pour vous ?</voice>."
        # speak_output += "<voice name=\"Mathieu\">Bienvenue chez Serenicia, que puis je faire pour vous ?</voice>."

        reprompt = "Dites aide pour savoir ce que je peux faire pour vous."
        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(reprompt)
                .response
        )


class PresentationIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return ask_utils.is_intent_name("PresentationIntent")(handler_input)

    def handle(self, handler_input):
        speak_output = "<say-as interpret-as=\"interjection\">Super </say-as>, Serenicia permet de prévenir les chutes et les appels à l'aide grâce à l'intelligence artificielle.<break time=\"500ms\"/> Serenicia propose une application famille, qui vous permettra de tout savoir sur votre parent en maison de retraite<break time=\"300ms\"/>, de passer des appels visio simplement par la voix, et bien plus encore !"
        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(speak_output)
                .response
        )


# Test to add a reminder
class AddReminderIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return ask_utils.is_intent_name("AddReminderIntent")(handler_input)

    def handle(self, handler_input):

        slots = handler_input.request_envelope.request.intent.slots
        reminder = slots['reminder'].value
        if reminder == "repas" or reminder == "dejeuner" or reminder == "dinner":
            time = "2021-07-20T11:30:00"
            freq = ["FREQ=DAILY;BYHOUR=11;BYMINUTE=30;BYSECOND=0;INTERVAL=1;",
                    "FREQ=DAILY;BYHOUR=18;BYMINUTE=00;BYSECOND=0;INTERVAL=1;"]
            sentence = "Le repas commence dans 30 minutes, tenez-vous pret !"
            text = "Notification de repas"
            if not check_if_reminder_exist(handler_input, text):
                speak_output = set_reminder(handler_input, time, freq, sentence, text)
            else:
                speak_output = "rappel deja programmé"
        else:
            speak_output = "Je n'ai pas compris votre demande, merci de réésayer."

        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(speak_output)
                .response
        )


class WhereConfiguredIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return ask_utils.is_intent_name("WhereConfiguredIntent")(handler_input)

    def handle(self, handler_input):
        device_id = handler_input.request_envelope.context.system.device.device_id  # Je récupère l'ID de Alexa
        dataJson = {'key': 'qaJyW9sytzLfVb8Uznfe6VGqU4IdGSyZi7foVbmZdbs', 'id': {device_id}, 'action': 'configured'}
        data = send_request_to_serenicia_server(dataJson)

        if not data['statut']:
            speak_output = "Je ne suis configuré dans aucune chambre. Si vous souhaitez me configurer, donnez moi la commande configuration"
        else:
            speak_output = "Je suis configuré dans la chambre " + str(data[
                                                                          'room_number']) + ",<break time=\"1s\"/> dites oui pour me déconfigurer, ou une commande pour continuer."
            session_attr = handler_input.attributes_manager.session_attributes
            session_attr["unconfigure"] = "unconfigure"
            session_attr["room_number"] = data['room_number']

        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(speak_output)
                .response
        )


class CheckPlanningIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return ask_utils.is_intent_name("CheckPlanningIntent")(handler_input)

    def handle(self, handler_input):
        device_id = handler_input.request_envelope.context.system.device.device_id
        dataJson = {'key': 'qaJyW9sytzLfVb8Uznfe6VGqU4IdGSyZi7foVbmZdbs', 'id': {device_id}, 'action': 'check_planning'}
        data = send_request_to_serenicia_server(dataJson)

        if not data['statut']:
            speak_output = "Pour connaitre vos rendez-vous, Alexa doit être configuré dans votre chambre. Dites configuration pour la configurer."
        elif data['event_type'] == "no_event":
            speak_output = "Vous n'avez pas de rendez-vous aujourd'hui"
        else:
            number = len(data["event_type"])
            speak_output = "Vous avez " + str(number) + " rendez-vous aujourd'hui. "
            for i in range(len(data["event_type"])):
                hour = data["event_date"]["hour"][i]
                minute = data["event_date"]["minute"][i]
                purpose = data['event_type'][i]
                contact = data['event_with_who'][i]
                if minute:
                    speak_output += "Avec " + contact + " à " + str(hour) + " heure " + str(minute) + ", "
                else:
                    speak_output += "Avec " + contact + ", à " + str(hour) + " heure, "
                if purpose:
                    speak_output += " par " + purpose + ", "
        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(speak_output)
                .response
        )


class VideoCallIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return ask_utils.is_intent_name("VideoCallIntent")(handler_input)

    def handle(self, handler_input):
        device_id = handler_input.request_envelope.context.system.device.device_id
        dataJson = {'key': 'qaJyW9sytzLfVb8Uznfe6VGqU4IdGSyZi7foVbmZdbs', 'id': {device_id}, 'action': 'video_call'}

        data = send_request_to_serenicia_server(dataJson)

        logger.info(data)

        if not data['statut']:
            speak_output = "Pour faire un appel vidéo, et trouver vos contact, Alexa doit être configuré dans votre chambre. Dites configuration pour la configurer."
            return (
                handler_input.response_builder
                    .speak(speak_output)
                    .ask(speak_output)
                    .response
            )
        else:
            name_entity = []
            repeat = "Qui souhaitez vous appeler ?"
            speak_output = "Vos contact disponibles sont :"
            for i in range(len(data['firstname'])):
                speak_output += data['firstname'][i] + data['lastname'][i] + ", "
                name_entity_synonyms = EntityValueAndSynonyms(
                    value=data['firstname'][i] + ' ' + data['lastname'][i], synonyms=[data['firstname'][i]]
                )
                name_entity.append(Entity(id=data['contact_id'][i], name=name_entity_synonyms))

            replace_entity_directive = DynamicEntitiesDirective(update_behavior=UpdateBehavior.REPLACE, types=[
                EntityListItem(name="NameSlotType", values=name_entity)], )

            # We send session attribute, to make video call launch only if there is contact saved in slots
            session_attr = handler_input.attributes_manager.session_attributes
            session_attr['contact'] = True

            speak_output += repeat

        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(repeat)
                .add_directive(replace_entity_directive)
                .response
        )


class LaunchVideoCallIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return ask_utils.is_intent_name("LaunchVideoCallIntent")(handler_input)

    def handle(self, handler_input):
        slots = handler_input.request_envelope.request.intent.slots

        name = slots['name'].value
        contact_id = get_id_of_contact(slots['name'])

        device_id = handler_input.request_envelope.context.system.device.device_id
        dataJson = {'key': 'qaJyW9sytzLfVb8Uznfe6VGqU4IdGSyZi7foVbmZdbs', 'id': {device_id},
                    'action': 'launch_video_call', 'contact': {contact_id}}
        data = send_request_to_serenicia_server(dataJson)

        session_attr = handler_input.attributes_manager.session_attributes
        if "contact" in session_attr:
            speak_output = "c'est parti, j'appelle " + name + " en visio."
        else:
            speak_output = "Dites je veux faire un appel visio pour choisir votre contact."
        return (
            handler_input.response_builder
                .speak(speak_output)
                .response
        )


class ConfigurationIntentHandler(AbstractRequestHandler):
    """Handler for Configuration Intent."""

    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("ConfigurationIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        device_id = handler_input.request_envelope.context.system.device.device_id  # Je récupère l'ID de Alexa
        slots = handler_input.request_envelope.request.intent.slots  # Je récupère le numéro de chambre
        room_number = slots['number'].value
        logger.warning(f'the device id is : {device_id}')
        dataJson = {'key': 'qaJyW9sytzLfVb8Uznfe6VGqU4IdGSyZi7foVbmZdbs', 'id': {device_id},
                    'room_number': {room_number}, 'action': 'configuration'}
        data = send_request_to_serenicia_server(dataJson)

        logger.info(data)

        if not data.get('statut'):
            speak_output = "La chambre numéro " + room_number + " n'existe pas."
        elif data.get('statut') == "set with same alexa":
            speak_output = "La chambre numéro " + room_number + " est déjà configuré avec cet appareil Alexa."
        elif data.get('statut') == "set with another alexa":
            session_attr = handler_input.attributes_manager.session_attributes
            session_attr["unconfigure"] = "unconfigure"
            session_attr["room_number"] = room_number
            speak_output = "La chambre numéro " + room_number + " est déjà configuré avec un autre appareil Alexa. <break time=\"500ms\"/> dites oui pour la déconfigurer, ou une commande pour continuer. "
        elif data.get('statut') == "set with another room":
            session_attr = handler_input.attributes_manager.session_attributes
            session_attr["unconfigure"] = "unconfigure"
            session_attr["room_number"] = data.get('room_number')
            speak_output = "Je suis déja configuré dans la chambre " + str(data.get(
                'room_number')) + ".<break time=\"500ms\"/>  Dites oui pour me déconfigurer de la chambre " + str(
                data.get('room_number')) + " ou une commande pour continuer"
        else:
            speak_output = "<audio src=\"soundbank://soundlibrary/ui/gameshow/amzn_ui_sfx_gameshow_neutral_response_03\"/> Ok, Alexa à bien été configuré dans la chambre" + room_number + "."
        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(speak_output)
                .response
        )


class WhoIsInRoomIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return ask_utils.is_intent_name('WhoIsInRoomIntent')(handler_input)

    def handle(self, handler_input):
        slots = handler_input.request_envelope.request.intent.slots
        room_number = slots['number'].value
        dataJson = {'key': 'qaJyW9sytzLfVb8Uznfe6VGqU4IdGSyZi7foVbmZdbs', 'action': 'check_who_is_there',
                    'room_number': {room_number}}
        data = send_request_to_serenicia_server(dataJson)

        logger.info(data)

        if not data['statut']:
            speak_output = "<say-as interpret-as=\"interjection\">Hmmm</say-as>, <amazon:emotion name=\"disappointed\" intensity=\"high\"> la chambre numéro " + room_number + " n'existe pas.</amazon:emotion>"

        else:
            normal_name = data['normal']
            phonetic = data['phonetic']
            list_of_name = []
            if not normal_name[0]:
                speak_output = "La chambre numéro " + room_number + " est vide."
            else:

                for i in range(len(normal_name)):
                    lastname = phonetic[i]['phonetic_lastname']
                    firstname = phonetic[i]['phonetic_firstname']
                    if lastname == None:
                        lastname = normal_name[i]['last_name']
                    if firstname == None:
                        firstname = normal_name[i]['first_name']

                    list_of_name.append({'firstname': firstname, 'lastname': lastname, 'next': ', '})

                speak_output = "Le résident de la chambre " + room_number + " est "

                for name in list_of_name:
                    speak_output += "<prosody rate=\"slow\">" + name['firstname'] + name['lastname'] + name[
                        'next'] + "</prosody>"

        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(speak_output)
                .response
        )


class LunchAndDinnerIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return ask_utils.is_intent_name("LunchAndDinnerIntent")(handler_input)

    def handle(self, handler_input):
        slots = handler_input.request_envelope.request.intent.slots
        when = slots['repas'].value
        if when == "midi" or when == "déjeuner":
            dataJson = {'key': 'qaJyW9sytzLfVb8Uznfe6VGqU4IdGSyZi7foVbmZdbs', 'action': 'what_we_eat', 'time': 'noon'}
        else:
            dataJson = {'key': 'qaJyW9sytzLfVb8Uznfe6VGqU4IdGSyZi7foVbmZdbs', 'action': 'what_we_eat',
                        'time': 'evening'}
        data = send_request_to_serenicia_server(dataJson)

        logger.info(data)

        if not data.get('statut'):
            speak_output = "Malheureusement, le chef n'a pas mis son menu à jour.."
        else:
            if when == "midi" or when == "déjeuner":
                speak_output = "A midi, le chef vous propose,"
            else:
                speak_output = "Ce soir, le chef vous propose,"
            if data.get('entry'):
                speak_output += data.get('entry') + "en entrée, "
            if data.get('main'):
                speak_output += data.get('main')
            if data.get('accompaniment'):
                speak_output += " avec " + data.get('accompaniment')
            speak_output += " en plat principal, "
            if data.get('dessert'):
                speak_output += " et " + data.get('dessert') + " en dessert."
            speak_output += "<say-as interpret-as=\"interjection\"> Bon appetit </say-as>"

        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(speak_output)
                .response
        )


class YesIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("AMAZON.YesIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        session_attr = handler_input.attributes_manager.session_attributes

        if "unconfigure" in session_attr:
            dataJson = {'key': 'qaJyW9sytzLfVb8Uznfe6VGqU4IdGSyZi7foVbmZdbs', 'action': session_attr["unconfigure"],
                        'room_number': session_attr['room_number']}
            data = send_request_to_serenicia_server(dataJson)
            speak_output = "<audio src=\"soundbank://soundlibrary/ui/gameshow/amzn_ui_sfx_gameshow_neutral_response_03\"/>Alexa n'est plus configuré dans la chambre " + str(
                session_attr['room_number']) + ". Pour la configurer, dites Configuration."

        else:
            speak_output = "Je n'ai pas compris"

        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(speak_output)
                .response
        )


class HelpIntentHandler(AbstractRequestHandler):  # Je doit pouvoir annoncer des exemples d'intent
    """Handler for Help Intent."""

    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("AMAZON.HelpIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        speak_output = "<say-as interpret-as=\"interjection\">Pas facile, hein? </say-as>, Vous pouvez me demander : "
        speak_output += "On mange quoi à midi ou ce soir, "
        speak_output += "Configuration, "
        speak_output += " Qui est dans la chambre 205,"
        speak_output += " Présente moi Serenicia"
        speak_output += " Je veux faire un appel vidéo"

        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(speak_output)
                .response
        )


class CancelOrStopIntentHandler(AbstractRequestHandler):
    """Single handler for Cancel and Stop Intent."""

    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return (ask_utils.is_intent_name("AMAZON.CancelIntent")(handler_input) or
                ask_utils.is_intent_name("AMAZON.StopIntent")(handler_input))

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        speak_output = "<say-as interpret-as=\"interjection\"> Au revoir</say-as> "  # <audio src=\"soundbank://soundlibrary/aircrafts/futuristic/futuristic_03\"/>"

        return (
            handler_input.response_builder
                .speak(speak_output)
                .response
        )


class FallbackIntentHandler(AbstractRequestHandler):
    """Single handler for Fallback Intent."""

    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("AMAZON.FallbackIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        logger.info("In FallbackIntentHandler")
        speech = "Je n'ai pas compris votre demande. Dites aide pour obtenir plus d'informations."
        reprompt = "Les choix possible sont : visioconférence, ouvrir les volets, fermer les volets, arréter les volets ?"

        return handler_input.response_builder.speak(speech).ask(reprompt).response


class SessionEndedRequestHandler(AbstractRequestHandler):
    """Handler for Session End."""

    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_request_type("SessionEndedRequest")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        # Any cleanup logic goes here.
        return handler_input.response_builder.response


class IntentReflectorHandler(AbstractRequestHandler):
    """The intent reflector is used for interaction model testing and debugging.
    It will simply repeat the intent the user said. You can create custom handlers
    for your intents by defining them above, then also adding them to the request
    handler chain below.
    """

    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_request_type("IntentRequest")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        intent_name = ask_utils.get_intent_name(handler_input)
        speak_output = "You just triggered " + intent_name + "."

        return (
            handler_input.response_builder
                .speak(speak_output)
                # .ask("add a reprompt if you want to keep the session open for the user to respond")
                .response
        )


class CatchAllExceptionHandler(AbstractExceptionHandler):
    """Generic error handling to capture any syntax or routing errors. If you receive an error
    stating the request handler chain is not found, you have not implemented a handler for
    the intent being invoked or included it in the skill builder below.
    """

    def can_handle(self, handler_input, exception):
        # type: (HandlerInput, Exception) -> bool
        return True

    def handle(self, handler_input, exception):
        # type: (HandlerInput, Exception) -> Response
        logger.error(exception, exc_info=True)

        speak_output = "<say-as interpret-as=\"interjection\">Hmmm</say-as>, je n'ai pas compris, veuillez répéter"

        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(speak_output)
                .response
        )


# The SkillBuilder object acts as the entry point for your skill, routing all request and response
# payloads to the handlers above. Make sure any new handlers or interceptors you've
# defined are included below. The order matters - they're processed top to bottom.


sb = CustomSkillBuilder(api_client=DefaultApiClient())

sb.add_request_handler(LaunchRequestHandler())
sb.add_request_handler(AddReminderIntentHandler())
sb.add_request_handler(PresentationIntentHandler())
sb.add_request_handler(WhoIsInRoomIntentHandler())
sb.add_request_handler(CheckPlanningIntentHandler())
sb.add_request_handler(ConfigurationIntentHandler())
sb.add_request_handler(WhereConfiguredIntentHandler())
sb.add_request_handler(LunchAndDinnerIntentHandler())
sb.add_request_handler(VideoCallIntentHandler())
sb.add_request_handler(LaunchVideoCallIntentHandler())
sb.add_request_handler(YesIntentHandler())
sb.add_request_handler(HelpIntentHandler())
sb.add_request_handler(CancelOrStopIntentHandler())
sb.add_request_handler(FallbackIntentHandler())
sb.add_request_handler(SessionEndedRequestHandler())
sb.add_request_handler(
    IntentReflectorHandler())  # make sure IntentReflectorHandler is last so it doesn't override your custom intent handlers

sb.add_exception_handler(CatchAllExceptionHandler())

lambda_handler = sb.lambda_handler()