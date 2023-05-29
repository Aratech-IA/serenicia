import asyncio
from django.views.decorators.csrf import csrf_exempt
import json
from glob import glob
import logging
from app1_base.log import Logger
import base64
from django.conf import settings
import websockets
from pathlib import Path
from app1_base.models import Client
from .models import ProfileSerenicia, MealBooking
from asgiref.sync import sync_to_async
from django.core.serializers import serialize

if 'log_api_ws' not in globals():
    log_api_ws = Logger('api_ws', level=logging.INFO).run()


@csrf_exempt
async def ws_profile_image(socket):
    await socket.accept()
    log_api_ws.warning('accept socket')
    list_key = [k.split('/')[-1] for k in glob(settings.MEDIA_ROOT + '/residents/*')]
    while True:
        try:
            data = await socket.receive_json()
            log_api_ws.warning(f'data is : {data}')
            if data['key'] in list_key:
                jpg_original = base64.b64decode(data['jpg'])  # Convert image back to binary
                if not data['profile']:
                    path = f"{settings.MEDIA_ROOT}/residents/{data['key']}/"
                else:
                    path = f"{settings.MEDIA_ROOT}/residents/{data['key']}/profile_pics/"
                    Path(path).mkdir(parents=True, exist_ok=True)
                log_api_ws.warning(f'jpg ready to write in {path} is  : {jpg_original}')
                with open(path+data['file_name'], 'wb') as file:
                    file.write(jpg_original)
                await socket.send_json({'answer': True})
            else:
                socket.send_json({'answer': False})
        except (json.decoder.JSONDecodeError, AssertionError, KeyError) as ex:
            log_api_ws.warning(f'Exception with the socket : {ex} /  name-->{type(ex).__name__}')
            try:
                await socket.send_json({'answer': False} )
            except websockets.exceptions.ConnectionClosed:
                log_api_ws.warning(f'connection is closed')
                break
    await socket.close()


# sync code ----------------------
def _get_client_key():
    return list(ProfileSerenicia.objects.all().values('folder'))


@csrf_exempt
async def ws_image_bytes(socket):
    await socket.accept()
    connexion = await socket.receive_json()
    try:
        if connexion.get('key') == settings.FACIAL_RECO_KEY:
            log_api_ws.warning('WS image bytes : accept socket')
            client = await sync_to_async(_get_client_key, thread_sensitive=True)()
            list_key = [i['folder'] for i in client]
            # list_key = [k.split('/')[-1] for k in glob(settings.MEDIA_ROOT + '/residents/*')]
            while True:
                try:
                    data = await socket.receive_json()
                    log_api_ws.warning(f'data is : {data}')
                    if data['key'] in list_key:
                        path = f"{settings.MEDIA_ROOT}/residents/{data['key']}/"
                        Path(path).mkdir(parents=True, exist_ok=True)
                        log_api_ws.warning(f'jpg ready to write in {path} ')
                        await socket.send_json({'answer': True})
                        data_bytes = await socket.receive_bytes()
                        log_api_ws.warning(f'image received  ')
                        with open(path + data['file_name'], 'wb') as file:
                            file.write(data_bytes)
                        log_api_ws.warning(f"written {data['file_name']} of {len(data_bytes)} bytes")
                        await socket.send_json({'answer': True})
                    else:
                        await socket.send_json({'answer': False})
                except (json.decoder.JSONDecodeError, KeyError, websockets.exceptions.ConnectionClosed,
                        AssertionError) as ex:
                    log_api_ws.warning(f'Exception with the socket : {ex} /  name-->{type(ex).__name__}')
                    break
        else:
            log_api_ws.warning(f'WS image bytes : invalid key {connexion.get("key")}')
    except KeyError:
        log_api_ws.warning('WS image bytes : no key received')
    await socket.close()


@sync_to_async
def get_latest_booking_update():
    return MealBooking.objects.latest('updated').updated


@csrf_exempt
async def reservation(socket):
    await socket.accept()
    origin = socket.headers['origin']
    local = settings.PUBLIC_SITE[:-1]
    log_api_ws.info(f'req from : {origin}')
    if local == origin:
        latest_update = await get_latest_booking_update()
        while True:
            try:
                tmp_datetime = await get_latest_booking_update()
                if latest_update != tmp_datetime:
                    latest_update = tmp_datetime
                    await socket.send_json('test')
                    await socket.receive_json()
                await asyncio.sleep(1)
            except websockets.exceptions.ConnectionClosed as ex:
                log_api_ws.warning(f'Exception with the socket : {ex} /  name-->{type(ex).__name__}')
                break
    await socket.close()


# ----------------------------------------------------------------------------------------------------

# Affichage clients en alerte
@csrf_exempt
async def client_in_alert(socket):
    await socket.accept()
    origin = socket.headers['origin']
    local = settings.PUBLIC_SITE[:-1]
    log_api_ws.info(f'req from : {origin}')
    if local == origin:
        list_id = await socket.receive_json()
        # print(list_id)
        while True:
            try:
                get_client_in_alert = await sync_to_async(list)(Client.objects.filter(alert__active=True, id__in=list_id).values_list('id', flat=True))
                # get_client_in_alert = [dict(t) for t in {tuple(d.items()) for d in get_client_in_alert}]
                await socket.send_json(get_client_in_alert)
                await asyncio.sleep(1)
            except websockets.exceptions.ConnectionClosed as ex:
                log_api_ws.warning(f'Exception with the socket : {ex} /  name-->{type(ex).__name__}')
                break
    await socket.close()
