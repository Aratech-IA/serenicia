import asyncio

from asgiref.sync import sync_to_async
from django.views.decorators.csrf import csrf_exempt
import json
import glob
import logging

from app1_base.models import Profile
from app1_base.log import Logger
from django.conf import settings
import websockets
import os
from pathlib import Path

from app4_ehpad_base.models import ProfileSerenicia

if 'log_api_download_videos' not in globals():
    log_api_video = Logger('log_api_download_videos', level=logging.INFO).run()


def _update_sended_status(list_folder):
    for value in list_folder:
        Profile.objects.filter(user__profileserenicia__folder=value['folder']).update(video_ready=False)


@csrf_exempt
async def send_parse_videos(socket):
    await socket.accept()
    connexion = await socket.receive_json()
    try:
        if connexion.get('key') == settings.FACIAL_RECO_KEY:
            log_api_video.info(f'WS send parse videos : key valid')
            while True:
                try:
                    list_folder = await sync_to_async(list)(
                        ProfileSerenicia.objects.filter(user__profile__video_ready=True).values('folder'))
                    temp_path = settings.MEDIA_ROOT + '/temp/'
                    list_path = []
                    for value in list_folder:
                        list_path += glob.glob(temp_path + value['folder'] + '/*.jpg')
                    if len(list_path) > 0:
                        await socket.send_json({'new_data': True})
                        question = await socket.receive_json()
                        if question['answer']:
                            running = True
                            while running:
                                try:
                                    for pict in list_path:
                                        with open(pict, "rb") as file:
                                            im = file.read()
                                        log_api_video.info(f'juste before sending metadata')
                                        await socket.send_json({'key': pict.split('/')[-2],
                                                                'nbr_of_pict': len(list_path),
                                                                'filename': pict.split('/')[-1],
                                                                })
                                        log_api_video.info(f'just after sending metadata')
                                        rep = await socket.receive_json()
                                        if rep['answer']:
                                            log_api_video.info(f'ready to send data')
                                            await socket.send_bytes(im)
                                            log_api_video.info(f'juste after sending')
                                            r = await socket.receive_json()
                                            if r['answer']:
                                                log_api_video.info(f'{r} / {pict}')
                                                list_path.remove(pict)
                                                os.remove(pict)
                                        if len(list_path) == 0:
                                            running = False
                                    await sync_to_async(_update_sended_status, thread_sensitive=True)(list_folder)
                                except (json.decoder.JSONDecodeError, KeyError, AssertionError) as ex:
                                    log_api_video.warning(
                                        f'Exception with the socket : {ex} /  name-->{type(ex).__name__}')
                    await asyncio.sleep(1)
                except websockets.exceptions.ConnectionClosed as ex:
                    log_api_video.info(f'connexion closed by client : {ex} /  name-->{type(ex).__name__}')
                    await socket.close()
        else:
            log_api_video.info(f'WS send parse videos : invalid key {connexion.get("key")}')
    except KeyError:
        log_api_video.info(f'WS send parse videos : no key received')
    await socket.close()


def _save_data(folder):
    try:
        if not Profile.objects.get(user__profileserenicia__folder=folder).photo:
            Profile.objects.filter(user__profileserenicia__folder=folder).update(photo='users_photo/' + folder + '.jpg')
    except Exception as ex:
        log_api_video.warning(f'profile_pic : Exception with the socket : {ex} /  name-->{type(ex).__name__}')


@csrf_exempt
async def receive_profile_pic(socket):
    await socket.accept()
    connexion = await socket.receive_json()
    try:
        if connexion.get('key') == settings.FACIAL_RECO_KEY:
            log_api_video.info(f'WS receive profile pic : key valid')
            receive = True
            while receive:
                try:
                    data = await socket.receive_json()
                    log_api_video.info(f"profile_pic : receive data {data['key']}")
                    await socket.send_json({'answer': True})
                    data_bytes = await socket.receive_bytes()
                    log_api_video.info(f'profile_pic : receive bytes')
                    path = f"{settings.MEDIA_ROOT}/users_photo/"
                    Path(path).mkdir(parents=True, exist_ok=True)
                    with open(path + data['key'] + '.jpg', 'wb') as file:
                        file.write(data_bytes)
                    log_api_video.info(f'profile_pic : user saved')
                    await socket.send_json({'answer': True})
                    receive = False
                    await sync_to_async(_save_data, thread_sensitive=True)(data['key'])
                except Exception as ex:
                    log_api_video.warning(f'profile_pic : Exception with the socket : {ex} /  name-->{type(ex).__name__}')
                    break
            await socket.close()
        else:
            log_api_video.info(f'WS receive profile pic : invalid key {connexion.get("key")}')
    except KeyError:
        log_api_video.info(f'WS receive profile pic : no key received')
    await socket.close()

