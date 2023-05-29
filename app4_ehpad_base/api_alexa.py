import asyncio
import logging
import pytz

from django.core.exceptions import ObjectDoesNotExist
from django.http import JsonResponse
from django.conf import settings

from app4_ehpad_base.models import Meal, ProfileSerenicia, \
    AlexaOrders, MotDirection, MotPoleSoins, MotHotelResto, MotCVS, EvalMenuSetting
from app15_calendar.models import PlanningEvent
from app1_base.log import Logger
from app6_care.models import Intervention, TaskLevel1, TaskLevel2, InterventionDetail
from app6_care.netsoins_api import post_intervention
from projet.settings.settings import TIME_ZONE
from .models import Client, Profile
from django.contrib.sessions.models import Session
from django.contrib.auth.models import User
from asgiref.sync import sync_to_async
from django.views.decorators.csrf import csrf_exempt
from datetime import datetime
from projet.settings import settings
from .views import get_data_photo_album

if 'log_api_alexa' not in globals():
    log_api_alexa = Logger('api_alexa', level=logging.ERROR, file=True).run()


@csrf_exempt
def get_action(request):
    """
    This is the entry point to add an action from alexa. The get_action record alexa action for a user
    :param request:
    :return: jsonResponse:
    """
    if request.method == 'POST':
        log_api_alexa.info(f'ALEXA >>> data are {request.POST}')
        key = request.POST.get('key', 'default')
        if key == settings.ALEXA_KEY:
            action = request.POST.get('action', 'default')

            param = {
                "alexa_id": request.POST.get('id', 'default'),
                "room_number": request.POST.get('room_number', 'default'),
                "time": request.POST.get('time', 'default'),
                "contact": request.POST.get('contact', 'default'),
                "type": request.POST.get('type', 'default'),
                "score": request.POST.get('score', 'default'),
                "album_name": request.POST.get('album_name', 'default'),
                "care": request.POST.get('care', 'default'),
            }

            dict_of_action = {
                "configuration": set_id_to_room,
                "configured": check_where_configured,
                "unconfigure": unconfigure_alexa_of_room,
                "check_who_is_there": get_resident_names,
                "what_we_eat": get_menu,
                "video_call": get_contact_for_video_call,
                "launch_video_call": launch_video_call_with_contact,
                "check_planning": get_planning_event,
                "back_to_index": back_to_index,
                "evalmenu": evalmenu,
                "announcement": announcement,
                "get_album": get_and_show_albums,
                "open_album": open_album,
                "new_care": add_new_care,
                "show_interventions": show_intervention_to_add,
            }

            json_answer = dict_of_action[action]

            for key, value in dict_of_action.items():
                if action == key:
                    if action == "configuration":
                        json_answer = value(param['alexa_id'], param['room_number'])
                    elif action in ("configured", "video_call", "check_planning", "back_to_index", "get_album",
                                    "show_interventions"):
                        json_answer = value(param['alexa_id'])
                    elif action in ("unconfigure", "check_who_is_there"):
                        json_answer = value(param['room_number'])
                    elif action == "what_we_eat":
                        json_answer = value(param['time'], param['alexa_id'])
                    elif action == "launch_video_call":
                        json_answer = value(param['contact'], param['alexa_id'])
                    elif action == "evalmenu":
                        json_answer = value(param['alexa_id'], param["type"], param["score"])
                    elif action == "announcement":
                        json_answer = value(param['type'])
                    elif action == "open_album":
                        json_answer = value(param['alexa_id'], param['album_name'])
                    elif action == "new_care":
                        json_answer = value(param["alexa_id"], param["care"])
                    else:
                        log_api_alexa.info('fonction pas trouvé...')

    log_api_alexa.info(f' Retour json vers Alexa is {json_answer}')
    if json_answer:
        return JsonResponse(json_answer, safe=False)
    else:
        return JsonResponse({'statut': False}, safe=False)


# ----------------------------------------------------------------------------------------------------------------------
# --------------------------------------------- WEBSOCKET ALEXA --------------------------------------------------------
# ----------------------------------------------------------------------------------------------------------------------

async def alexa_order(socket):
    """
    This socket send push redirect to the site in order to change the current page. This is used to navigate the site
    with Alexa
    :param socket:
    :return:
    """
    await socket.accept()
    log_api_alexa.debug(f'ALEXA WEBSOCKET  >>> headers are {socket.headers.as_dict()}')
    origin = socket.headers['origin']
    log_api_alexa.debug(f'ALEXA WEBSOCKET  >>> origin is {origin}')
    cookie = socket.headers['cookie']
    csrf_token = cookie.split('csrftoken=')[1].split(';')[0]
    sessionid = cookie.split('sessionid=')[1].split(';')[0]
    log_api_alexa.debug(f'ALEXA WEBSOCKET  >>> csrf is {csrf_token} / sessionid is {sessionid}')
    session_rq = sync_to_async(_get_session, thread_sensitive=True)
    session = await session_rq(sessionid)
    session_data = session.get_decoded()

    # I get user objects (resident who launch the call)
    uid = session_data.get('_auth_user_id')
    user_rq = sync_to_async(_get_user, thread_sensitive=True)
    user = await user_rq(uid)
    alexa_id_rq = sync_to_async(_get_alexa_id, thread_sensitive=True)
    alexa_id = await alexa_id_rq(user)
    log_api_alexa.debug(f'ALEXA WEBSOCKET  >>> user is {user}')

    while True:
        try:
            get_order_rq = sync_to_async(_get_order_type, thread_sensitive=True)
            order_type = await get_order_rq(alexa_id)
            if order_type == 'visio_call':
                contact_rq = sync_to_async(_get_contact, thread_sensitive=True)
                contact = await contact_rq(alexa_id)
                log_api_alexa.debug(f'ALEXA WEBSOCKET >>> contact is {contact}')
                get_token_video_rq = sync_to_async(_get_token_video, thread_sensitive=True)
                token_video = await get_token_video_rq(contact)
                # url = origin + '/videochat/call/?selected=' + str(token_video)
                url = origin + '/app13_resident/videochat/call/?selected=' + str(token_video)
                log_api_alexa.debug(f'ALEXA WEBSOCKET >>> url is {url}')
                await socket.send_json({'redirect': url})
                await socket.receive_json()
                log_api_alexa.debug(f'ALEXA >>> json with video Chat\'s URL sent to WS customer')
                clean_table_rq = sync_to_async(_clean_table, thread_sensitive=True)  # I delete the order from table
                await clean_table_rq(alexa_id, order_type)
            elif order_type == 'get_contact':
                url = origin + '/app13_resident/videochat/'
                await socket.send_json({'redirect': url})
                await socket.receive_json()
                log_api_alexa.debug(f'ALEXA >>> json with videochat\'s URL with contact sent to WS customer')
                clean_table_rq = sync_to_async(_clean_table, thread_sensitive=True)
                await clean_table_rq(alexa_id, order_type)
            elif order_type == 'back_to_index':
                url = origin + '/app13_resident/'
                log_api_alexa.debug(f'ALEXA WEBSOCKET >>> url is {url}')
                await socket.send_json({'redirect': url})
                await socket.receive_json()
                log_api_alexa.debug(f'ALEXA >>> json with index\'s URL sent to WS customer')
                clean_table_rq = sync_to_async(_clean_table, thread_sensitive=True)
                await clean_table_rq(alexa_id, order_type)
            elif order_type == 'evalmenu_start':
                url = origin + '/app13_resident/menus/entree/manual/'
                await socket.send_json({'redirect': url})
                await socket.receive_json()
                log_api_alexa.debug(f'ALEXA WEBSOCKET>>> json with index\'s URL sent to WS customer')
                clean_table_rq = sync_to_async(_clean_table, thread_sensitive=True)
                await clean_table_rq(alexa_id, order_type)
            elif order_type in ('evalmenu_entree', 'evalmenu_main', 'evalmenu_dessert', 'evalmenu_service'):
                get_evalmenu_data_rq = sync_to_async(_get_evalmenu_data, thread_sensitive=True)
                score = await get_evalmenu_data_rq(alexa_id, order_type)
                await socket.send_json({'redirect': 'empty', 'score': score})
                await socket.receive_json()
                clean_table_rq = sync_to_async(_clean_table, thread_sensitive=True)
                await clean_table_rq(alexa_id, order_type)
            elif order_type == 'show_menu':
                url = origin + '/app13_resident/menus/'
                await socket.send_json({'redirect': url})
                await socket.receive_json()
                log_api_alexa.debug(f'ALEXA >>> json with menu\'s URL sent to WS customer')
                clean_table_rq = sync_to_async(_clean_table, thread_sensitive=True)
                await clean_table_rq(alexa_id, order_type)
            elif order_type == 'show_albums':
                url = origin + '/app13_resident/albums/'
                await socket.send_json({'redirect': url})
                await socket.receive_json()
                log_api_alexa.debug(f'ALEXA >>> json with albums list\'s URL sent to WS customer')
                clean_table_rq = sync_to_async(_clean_table, thread_sensitive=True)
                await clean_table_rq(alexa_id, order_type)
            elif order_type == 'open_album':
                get_album_name_rq = sync_to_async(_get_album_name, thread_sensitive=True)
                album_name = await get_album_name_rq(alexa_id, order_type)
                url = origin + '/app13_resident/albums/' + str(album_name) + '/'
                await socket.send_json({'redirect': url})
                await socket.receive_json()
                log_api_alexa.debug(f'ALEXA >>> json with chosen albums\'s URL sent to WS customer')
                clean_table_rq = sync_to_async(_clean_table, thread_sensitive=True)
                await clean_table_rq(alexa_id, order_type)
            elif order_type == 'show_intervention':
                url = origin + '/app13_resident/interventions/'
                await socket.send_json({'redirect': url})
                await socket.receive_json()
                log_api_alexa.debug(f'ALEXA >>> json with intervention\'s URL sent to WS customer')
                clean_table_rq = sync_to_async(_clean_table, thread_sensitive=True)
                await clean_table_rq(alexa_id, order_type)
            await asyncio.sleep(1)
        except Exception as ex:
            log_api_alexa.debug(f'Exception with the socket : {ex} /  name-->{type(ex).__name__}')
            break
    await socket.close()


# |--------------------|
# |  sync sql request  |
# |--------------------|


def _get_user(uid):
    try:
        user = User.objects.get(id=uid)
        return user
    except ObjectDoesNotExist:
        return False


def _get_session(sessionid):
    try:
        session = Session.objects.get(session_key=sessionid)
        return session
    except ObjectDoesNotExist:
        return False


def _get_alexa_id(user):
    try:
        profile = Profile.objects.get(user=user)
    except ObjectDoesNotExist:
        return False
    if profile:
        return profile.client.alexa_device_id
    else:
        return False


def _get_order_type(alexa_id):
    try:
        order = AlexaOrders.objects.filter(alexa_device_id=alexa_id).last()
        if order:
            return order.order_type
        else:
            return False
    except ObjectDoesNotExist:
        return False


def _get_contact(alexa_id):
    try:
        contact = AlexaOrders.objects.get(alexa_device_id=alexa_id, order_type='visio_call')
    except ObjectDoesNotExist:
        return False
    if contact:
        return contact.video_call_contact_id
    else:
        return False


def _get_token_video(contact):
    try:
        token_video = ProfileSerenicia.objects.get(user=contact)
    except ObjectDoesNotExist:
        return False
    if token_video:
        return token_video.token_video_call
    else:
        return False


def _get_evalmenu_data(alexa_id, type):
    try:
        score = AlexaOrders.objects.get(alexa_device_id=alexa_id, order_type=type)
    except ObjectDoesNotExist:
        return False
    if score:
        return score.score
    else:
        return False


def _get_album_name(alexa_id, type):
    try:
        album_name = AlexaOrders.objects.get(alexa_device_id=alexa_id, order_type=type)
        album_name = album_name.score
    except ObjectDoesNotExist:
        return False
    if album_name:
        return album_name
    else:
        return False


def _clean_table(alexa_id, order_type):
    AlexaOrders.objects.filter(alexa_device_id=alexa_id, order_type=order_type).delete()


# ----------------------------------------------------------------------------------------------------------------------
# --------------------------------------------- ALEXA FUNCTION ---------------------------------------------------------
# ----------------------------------------------------------------------------------------------------------------------


# Function to get menu of the day (lunch or dinner)
def get_menu(time, alexa_id):
    x = AlexaOrders(alexa_device_id=alexa_id, order_type='show_menu')
    x.save()
    meal = Meal.objects.filter(date=datetime.now().date(), type=time)
    if meal.exists():
        menu = {
            'statut': True
        }
        if meal[0].entree:
            menu['entry'] = meal[0].entree.name
        if meal[0].main_dish:
            menu['main'] = meal[0].main_dish.name
        if meal[0].accompaniment:
            menu['accompaniment'] = meal[0].accompaniment.name
        if meal[0].dessert:
            menu['dessert'] = meal[0].dessert.name

        if len(menu.keys()) < 3:
            return False
        else:
            log_api_alexa.info(menu)
            return menu
    else:
        return False


# Function to get residents name and firstname
def get_resident_names(room_number):
    room_exists = Client.objects.filter(room_number=room_number).exists()
    if not room_exists:
        log_api_alexa.info(room_exists)  # Send False if room doesn't exist
        return room_exists
    a = Profile.objects.filter(client__room_number=room_number).values('phonetic_lastname',
                                                                       'phonetic_firstname')  # Find phonetic name
    a = list(a)
    x = User.objects.filter(profile__client__room_number=room_number).values('last_name',
                                                                             'first_name')  # then i find name of residents
    x = list(x)
    if not x:  # If no resident, i fill data with empty name
        x.append(False)
    names = {"normal": x, "phonetic": a, "statut": True}  # Dict with both list
    log_api_alexa.info(names)
    return names  # Return my list of name and my list of phonetic names


# Function checks if room exist, if yes, add alexa id to bdd
def set_id_to_room(alexa_id, room_number):
    x = Client.objects.filter(room_number=room_number)
    alexa = Client.objects.filter(alexa_device_id=alexa_id)
    if x.exists():
        x = x[0].alexa_device_id
        if alexa.exists():
            room_number = alexa[0].room_number
            return {"statut": "set with another room", "room_number": room_number}
        elif x == alexa_id:
            return {"statut": "set with same alexa"}
        elif x != alexa_id and x != "not set up":
            return {"statut": "set with another alexa"}
        else:
            x = Client.objects.get(room_number=room_number)
            x.alexa_device_id = alexa_id
            x.save()
            return {"statut": True}
    else:
        return False


# Check in which room alexa is configured
def check_where_configured(alexa_id):
    x = Client.objects.filter(alexa_device_id=alexa_id)
    if x.exists():
        x = x[0].room_number
        return {"statut": True, "room_number": x}
    else:
        return False


# Delete alexa id from bdd in room.
def unconfigure_alexa_of_room(room_number):
    x = Client.objects.filter(room_number=room_number)
    x = x[0]
    x.alexa_device_id = 'not set up'
    x.save()
    return {"statut": True}


# Get contact available of the resident, for video call
def get_contact_for_video_call(alexa_id):
    x = Client.objects.filter(alexa_device_id=alexa_id)
    if x.exists():
        x = x[0].room_number
        x = ProfileSerenicia.objects.filter(user_list__client__room_number=x, user__groups__permissions__codename='view_family')
        list_of_contact = {'firstname': [], 'lastname': [], 'contact_id': [], 'statut': True}
        if x:
            for user in x:
                list_of_contact['firstname'].append(user.user.first_name)
                list_of_contact['lastname'].append(user.user.last_name)
                list_of_contact['contact_id'].append(user.user.pk)
        else:
            list_of_contact = {'firstname': 'empty', 'statut': True}

        send_order = AlexaOrders(alexa_device_id=alexa_id, order_type='get_contact')
        send_order.save()
        return list_of_contact
    else:
        return False


# Launch vidéo call with selected contact
def launch_video_call_with_contact(contact_pk, alexa_id):
    try:
        contact = User.objects.get(pk=contact_pk)
        send_order = AlexaOrders(alexa_device_id=alexa_id, video_call_contact_id=contact, order_type='visio_call')
        send_order.save()
        return True
    except ObjectDoesNotExist:
        return False


# Get social planning of resident in room. NEVER GET INTO FUNCTION, DONO Y...
def get_planning_event(alexa_id):
    log_api_alexa.info(f'je suis dans la fonction get planning event')
    try:
        x = Client.objects.get(alexa_device_id=alexa_id)
    except ObjectDoesNotExist:
        return False
    t = PlanningEvent.objects.filter(participants__user__profile__client__room_number=x.room_number,
                                     start__date=datetime.now().date())
    log_api_alexa.info(f'Voici le planning : {t}')
    if t:
        time_of_event = {"hour": [], "minute": []}
        event_with_who = []
        event_for_what = []
        for x in range(len(t)):
            utc_fr = t[x].event_date.astimezone(pytz.timezone("Europe/Paris"))
            time_of_event["hour"].append(utc_fr.hour)
            time_of_event["minute"].append(utc_fr.minute)
            event_with_who.append(t[x].user.first_name)
            event_for_what.append(t[x].event_type.task)
        return {"statut": True, "event_type": event_for_what, "event_date": time_of_event, "event_with_who": event_with_who}
    else:
        return {"statut": True, "event_type": "no_event"}


def back_to_index(alexa_id):
    try:
        send_order = AlexaOrders(alexa_device_id=alexa_id, order_type='back_to_index')
        send_order.save()
        return True
    except ObjectDoesNotExist:
        return False


def evalmenu(alexa_id, type, score):
    try:
        if EvalMenuSetting.objects.exists():
            switch = EvalMenuSetting.objects.get().notation_switch
        else:
            # Default settings on 16pm UTC
            switch = datetime.strptime("16:00", "%H:%M").time()
        if switch > datetime.now().time():
            menutype = "noon"
        else:
            menutype = "evening"
        today_menu = Meal.objects.filter(date=datetime.today().date(), type=menutype)
        if len(today_menu) < 1:
            return False
        try:
            send_order = AlexaOrders(alexa_device_id=alexa_id, order_type=type, score=score)
            send_order.save()
            return {'statut': True}
        except ObjectDoesNotExist:
            return False
    except ObjectDoesNotExist:
        return False


def announcement(type):
    try:
        if type == "1":
            announce = MotDirection.objects.last()
        elif type == "2":
            announce = MotPoleSoins.objects.last()
        elif type == "3":
            announce = MotHotelResto.objects.last()
        else:
            announce = MotCVS.objects.last()
        return {'statut': True, 'title': announce.object, 'text': announce.text}
    except ObjectDoesNotExist:
        return False


def get_and_show_albums(alexa_id):
    try:
        resident = User.objects.get(profile__client__alexa_device_id=alexa_id)
        resident = User.objects.get(pk=resident.pk)
        folder = resident.profileserenicia.folder
        albums = get_data_photo_album(folder)
        log_api_alexa.debug(albums)
        list_album = []
        if albums:
            for album in albums:
                list_album.append(album.get('name'))
            if list_album:
                try:
                    send_order = AlexaOrders(alexa_device_id=alexa_id, order_type='show_albums')
                    send_order.save()
                    return {'list_album': list_album, 'statut': True}
                except ObjectDoesNotExist:
                    return False
        else:
            return {'list_album': 'empty', 'statut': True}
    except ObjectDoesNotExist:
        return False


def open_album(alexa_id, album_name):
    try:
        send_order = AlexaOrders(alexa_device_id=alexa_id, order_type='open_album', score=album_name)
        send_order.save()
        return {'statut': True}
    except ObjectDoesNotExist:
        return False


def add_new_care(alexa_id, care):
    date = datetime.now().astimezone(pytz.timezone(TIME_ZONE))
    nurse = User.objects.get(pk=3056)
    try:
        user = User.objects.get(profile__client__alexa_device_id=alexa_id)
    except ObjectDoesNotExist:
        return False
    if care == "pipi":
        task_level1 = TaskLevel1.objects.get(name="Mise aux toilettes")
        task_detail = TaskLevel2.objects.get(name="Urine")
    elif care == "caca":
        task_level1 = TaskLevel1.objects.get(name="Mise aux toilettes")
        task_detail = TaskLevel2.objects.get(name="Selle")
    elif care == "douche":
        task_level1 = TaskLevel1.objects.get(name="Douche")
        task_detail = TaskLevel2.objects.get(name="Douche")
    elif care == "brosser les dents":
        task_level1 = TaskLevel1.objects.get(name="Douche")
        task_detail = TaskLevel2.objects.get(name="Hygiène bucco dentaire")
    # ADD CHANGER COUCHE ET CHANGER VETEMENTS
    try:
        add_new_intervention = Intervention(type=task_level1, nurse=nurse, patient=user, start=date, end=date)
        add_new_intervention.save()
        task_detail_instance = InterventionDetail.objects.create(task_level_2=task_detail)
        add_new_intervention.details.add(task_detail_instance)
        # Send intervention to Netsoin API
        post_intervention(add_new_intervention)
    except ObjectDoesNotExist:
        return False
    return {'statut': True}


def show_intervention_to_add(alexa_id):
    try:
        add_order = AlexaOrders(alexa_device_id=alexa_id, order_type="show_intervention")
        add_order.save()
        return {'statut': True}
    except ObjectDoesNotExist:
        return False