import asyncio
import logging
from pathlib import Path

from PIL import Image, ImageOps
from asgiref.sync import sync_to_async
from django.core.exceptions import ObjectDoesNotExist
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt

from app15_calendar.models import PlanningEventPhotos
from app1_base.log import Logger
from app4_ehpad_base.models import Photos, ProfileSerenicia
from app10_social_activities.models import Photo as ActivityPhoto
from app4_ehpad_base.notifs import send_notif_new_photo_to_family

if 'log_api_ws_reco' not in globals():
    log_api_ws = Logger('log_api_ws_reco', level=logging.INFO, file=True).run()


def _is_photos_empty():
    if Photos.objects.count() > 0:
        return False
    return True


def _get_photos_to_send():
    p = Path(settings.MEDIA_ROOT + '/tmp_photos')
    path_list = list(p.glob('*'))
    names = ["tmp_photos/" + str(name).split('/')[-1] for name in path_list]
    Photos.objects.exclude(file__in=names).delete()
    return list(Photos.objects.filter(file__in=names))


def create_thumbnail(path_file, path_thumb):
    picture = Image.open(path_file)
    picture.thumbnail((10000, 500))
    Path(path_thumb).mkdir(exist_ok=True)
    picture.save(path_thumb + path_file.split('/')[-1])


def rotation_image(path_file):
    picture = Image.open(path_file)
    rotate_picture = ImageOps.exif_transpose(picture)
    rotate_picture.save(path_file)


def save_photo(photo, path_folder):
    Path(path_folder).mkdir(exist_ok=True, parents=True)
    path_file = path_folder + photo.date_add.date().strftime('%Y-%m-%d') + '_' + photo.file.name.split('/')[-1]
    with open(path_file, 'wb+') as destination:
        for chunk in photo.file.chunks():
            destination.write(chunk)
    rotation_image(path_file)
    create_thumbnail(path_file, f'{path_folder}/thumbnails/')
    return path_file


def get_activity_thumbnail_path(img_path):
    result = img_path.split('/')
    result.pop(0)
    result.pop(-1)
    result = str().join(['/' + elem for elem in result])
    return f'{result}/thumbnails/'


def save_activity_photo(photo, list_folders):
    photo_activity = ActivityPhoto.objects.create(activity_new=photo.planningeventphotos.planning_event)
    photo_activity.img.save(photo.file.name.split('/')[-1], photo.file)
    rotation_image(photo_activity.img.path)
    create_thumbnail(photo_activity.img.path, get_activity_thumbnail_path(photo_activity.img.path))
    identified = ProfileSerenicia.objects.filter(folder__in=list_folders)
    photo_activity.identified.add(*identified)
    [photo.planningeventphotos.planning_event.attendance.add(profileserenicia)
     for profileserenicia in identified if
     profileserenicia in photo.planningeventphotos.planning_event.participants.all()]


def _handle_photo(photo, list_folders):
    public = True
    try:
        public = photo.planningeventphotos.planning_event.event.public
        save_activity_photo(photo, list_folders)
    except ObjectDoesNotExist:
        pass
    if list_folders != 'no face':
        for folder in list_folders:
            if ProfileSerenicia.objects.filter(folder=folder).exists():
                path_folder = f'{settings.MEDIA_ROOT}/residents/{folder}/'
                save_photo(photo, path_folder)
                if not PlanningEventPhotos.objects.filter(photos=photo).exists():
                    send_notif_new_photo_to_family(folder)
    if public:
        path_common = f'{settings.MEDIA_ROOT}/common/'
        save_photo(photo, path_common)
    photo.file.delete()
    photo.delete()


# sert uniquement à débloquer les photos publiques en local (skip le traitement face reco)
# def save_shell():
#     for photo in _get_photos_to_send():
#         _handle_photo(photo, [])


def _get_list_resident(photo):
    if PlanningEventPhotos.objects.filter(photos=photo).exists():
        result = photo.planningeventphotos.planning_event.participants.values('folder')
    else:
        result = ProfileSerenicia.objects.filter(
            user__groups__permissions__codename__in=['view_residentehpad', 'view_residentrss', ],
            user__is_active=True, status='home').values('folder')
    return list(result)


@csrf_exempt
async def multiple_faces(socket):
    try:
        await socket.accept()  # Dobby is free
        connexion = await socket.receive_json()
        if connexion.get('key') == settings.FACIAL_RECO_KEY:
            # log_api_ws.info(f'WS multiple faces : key valid')
            while True:
                if not await sync_to_async(_is_photos_empty)():
                    list_photos = await sync_to_async(_get_photos_to_send, thread_sensitive=True)()
                    for photo in list_photos:
                        await socket.send_json({'start': True})
                        for chunk in photo.file.chunks():
                            await socket.send_bytes(chunk)
                        await socket.send_json({'end': True})
                        answer = await socket.receive_json()
                        if answer.get('received'):
                            list_resident = await sync_to_async(_get_list_resident, thread_sensitive=True)(photo)
                            await socket.send_json(list_resident)
                            list_folders = await socket.receive_json()
                            if list_folders.get('result'):
                                await sync_to_async(_handle_photo, thread_sensitive=True)(photo,
                                                                                          list_folders.get('result'))
                else:
                    await asyncio.sleep(2)
        else:
            log_api_ws.info(f'WS multiple faces : invalid key {connexion.get("key")}')
    except KeyError:
        log_api_ws.info(f'WS multiple faces : no key received')
    await socket.close()
