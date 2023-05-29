import asyncio
import logging
from django.utils import timezone
from django.contrib.auth.models import User
from datetime import timedelta
from asgiref.sync import sync_to_async
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt

from app1_base.log import Logger
from app1_base.models import Result

if 'log_api_reco_on_cam' not in globals():
    log_api_ws = Logger('log_api_reco_on_cam', level=logging.INFO).run()

def _is_objs_faces_empty(res):
    if res.count() > 0:
        return False
    return True

def _objs_face_detected():
    res = Result.objects.filter(object__result_object__contains='face',
                                time__gte=timezone.localtime()-timedelta(minutes=15),face_check=False)
    return res

def _update_face_check(result):
    Result.objects.filter(id=result).update(face_check=True)

def _handle_face_list(faces_reco, id):
    if faces_reco != 'no face':
        identified = User.objects.filter(profileserenicia__folder__in=faces_reco)
        res = Result.objects.get(id=id)
        res.users.add(*identified)

@csrf_exempt
async def reco_on_cam(socket):
    try:
        await socket.accept()  # Dobby is free
        connexion = await socket.receive_json()
        if connexion.get('key') == settings.FACIAL_RECO_KEY:
            log_api_ws.info(f'WS reco_on_cam: key valid')
            while True:
                objs_faces = await sync_to_async(_objs_face_detected)()
                if not await sync_to_async(_is_objs_faces_empty)(objs_faces):
                    for obj in objs_faces:
                        path_picture = f"{settings.MEDIA_ROOT}/{obj.file.split('.')[-2]}_no_box.jpg"
                        try :
                            with open(path_picture, "rb") as file:
                                im = file.read()
                        except FileNotFoundError:
                            log_api_ws.info(f"WS reco_on_cam: path to picture doesn't exist yet")
                            continue
                        await socket.send_json({'start': True})
                        log_api_ws.info(f'WS reco_on_cam: path to picture exist')
                        await socket.send_bytes(im)
                        answer = await socket.receive_json()
                        if answer.get('received'):
                            await sync_to_async(_update_face_check)(obj.id)
                            list_folders = await socket.receive_json()
                            await sync_to_async(_handle_face_list)(list_folders, obj.id)
                else:
                    await asyncio.sleep(2)
        else:
            log_api_ws.info(f'WS reco_on_cam : invalid key {connexion.get("key")}')
    except KeyError:
        log_api_ws.info(f'WS reco_on_cam : no key received')
    await socket.close()