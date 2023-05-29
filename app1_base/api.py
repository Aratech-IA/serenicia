# -*- coding: utf-8 -*-
"""
Created on Thu Dec 26 10:34:51 2019

@author: julien
"""
import asyncio
import glob
import json
import logging
import os
import subprocess
import time
from datetime import datetime

import pytz
from PIL import Image, ImageFont, ImageDraw
from asgiref.sync import async_to_sync, sync_to_async
from django.conf import settings
from django.db import IntegrityError
from django.db import transaction
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from websockets.exceptions import ConnectionClosedError
from django.db.models import Count
import secrets
from io import BytesIO
from functools import partial
# from collections import Counter
# from .check_alert_signal import check_result

from .log import Logger
from .utils import redress_coordinate
from .models import Camera, Result, Client, Object, MachineID, CameraUri, AlertStuffsChoice

if 'log_api' not in globals():
    log_api = Logger('api', level=logging.ERROR).run()


def _purge_files(client):
    # to remove all the image on disk which are not in the result
    r = Result.objects.filter(camera__client=client)
    r_file = [i.file.split('/')[1][:28] for i in r]
    path = os.path.join(settings.MEDIA_ROOT, client.folder)
    os.chdir(path)
    fd = 0
    for file in glob.glob("*.jpg"):
        if file[:4] != 'temp':  # do not clear the temp image
            if file[:28] not in r_file:
                os.remove(os.path.join(settings.MEDIA_ROOT, client.folder, file))
                fd += 1
    return fd


def _delete_space(client):
    # check the space on disk to respect the quota
    path = os.path.join(settings.MEDIA_ROOT, client.folder)
    try:
        size = int(subprocess.check_output(['du', '-s', path]).split()[0].decode('utf-8').split('M')[0])
        log_api.info(f'the space for image on disk is {size/1000} MO')
        if size > client.space_allowed * 1000:
            r_to_delete = Result.objects.filter(camera__client=client).order_by('id')[:300]
            for im_d in r_to_delete:
                if 'jpg' in im_d.file:
                    try:
                        os.remove(os.path.join(settings.MEDIA_ROOT, im_d.file))
                        os.remove(os.path.join(settings.MEDIA_ROOT, im_d.file.split('.jpg')[0] + '_no_box.jpg'))
                    except OSError:
                        pass
                im_d.delete()
            _purge_files(client)
    except subprocess.CalledProcessError:
        pass





@sync_to_async
@csrf_exempt
@async_to_sync
async def upload_image(request):
    if request.method == 'POST':
        log_api.info(f'IMAGE >>> data are    {request.POST}')
        key = request.POST.get('key', 'default')
        img_name = request.POST.get('img_name', 'default')
        cam = request.POST.get('cam', 'default')
        result = request.POST.get('result', False)
        real_time = request.POST.get('real_time', True)
        resize_factor = float(request.POST.get('resize_factor', 1))
        try:
            client = await sync_to_async(Client.objects.get, thread_sensitive=True)(key=key)
            camera = await sync_to_async(Camera.objects.get, thread_sensitive=True)(pk=cam)
        except (Client.DoesNotExist, Camera.DoesNotExist):
            await asyncio.sleep(10)
            pass
            return JsonResponse({'statut': False}, safe=False)
        img = request.FILES['myFile']
        size = len(img)
        img_path = settings.MEDIA_ROOT + '/' + client.folder + '/' + img_name
        os.makedirs(os.path.dirname(img_path), exist_ok=True)
        await sync_to_async(_delete_space,  thread_sensitive=True)(client)
        if real_time == 'False':
            with open(img_path + '_no_box.jpg', 'wb') as file:
                file.write(img.read())
        img_pil = Image.open(img)
        draw = ImageDraw.Draw(img_pil)
        result_filtered = json.loads(result)
        log_api.debug(f'IMAGE >>> result filtered are   {result_filtered} size is {img_pil.size}')
        for r in result_filtered:
            outline = "green" if r[2][2] * r[2][3] > camera.max_object_area_detection else "red"
            box = ((int((r[2][0] - (r[2][2] / 2)) * resize_factor),
                    int((r[2][1] - (r[2][3] / 2)) * resize_factor)),
                   (int((r[2][0] + (r[2][2] / 2)) * resize_factor),
                    int((r[2][1] + (r[2][3] / 2)) * resize_factor)))
            log_api.debug(f'IMAGE >>> box for {r} is {box}')
            draw.rectangle(box, outline=outline, width=int(3 * resize_factor) + 1)
            draw.text(box[1], r[0], fill=outline,
                      font=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                                              int(30 * resize_factor)))
        img_pil.save(img_path + '.jpg', "JPEG")
        log_api.info(f'saving image >>> {img_path}')
        return JsonResponse([{'size': size, 'name': img_path}, ], safe=False)
    return JsonResponse([{'statut': 'ko', }, ], safe=False)


# --------------------------SQL async request ------------------------------------------------------
def _set_result(data, camera, client):
    with transaction.atomic():
        result_db = Result(camera=camera, file=client.folder + '/' + data['img'], video=data['video'],
                           brut=data['result_darknet'], correction=data['correction'])
        result_db.save()
        log_api.debug(f'Saved result_db   {result_db}')
        for r in data['result_filtered']:
            log_api.debug(f'Saving object   {r}')
            object_db = Object(result=result_db,
                               result_object=r[0],
                               result_prob=r[1],
                               result_loc1=r[2][0],
                               result_loc2=r[2][1],
                               result_loc3=r[2][2],
                               result_loc4=r[2][3])
            object_db.save()
# --------------------------------------------------------------------------------------------------


@sync_to_async
@csrf_exempt
@async_to_sync
async def upload_result(request):
    data = json.loads(request.body.decode())

    try:
        client = await sync_to_async(Client.objects.get, thread_sensitive=True)(key=data['key'])
        camera = await sync_to_async(Camera.objects.get, thread_sensitive=True)(pk=data['cam'])
    except (Client.DoesNotExist, Camera.DoesNotExist):
        await asyncio.sleep(10)
        pass
        return JsonResponse({'statut': False}, safe=False)
    log_api.info(f'received result from client  {client.adress_lieu} for cam {camera.name} -> {data} ')
    await sync_to_async(_set_result, thread_sensitive=True)(data, camera, client)
    return JsonResponse([{'statut': True}, ], safe=False)


# --------------------   SQL async request --------------------------------------------------------
def _set_cam(cam, client):
    modified = False
    for ip, values in cam.items():
        uri = values.pop('uri', None)
        # remove the keys used for live state
        values.pop('on_camera_LD', None)
        values.pop('on_camera_HD', None)
        values.pop('on_rec', None)
        values.pop('change', None)
        try:
            objects, created = Camera.objects.get_or_create(client=client, ip=ip, defaults=values)
        except IntegrityError:  # the serial number already exist !
            log_api.info(f'the serial number already exists')
            serial = values.pop('serial_number', None)
            values['ip'] = ip
            # values.pop('name', None)  # let the name
            objects, created = Camera.objects.update_or_create(client=client,
                                                               serial_number=serial,
                                                               defaults=values)
            created = True
        if not created:
            if not objects.serial_number and values['serial_number']:
                is_cam_serial_setup = Camera.objects.filter(client=client, serial_number=values['serial_number'])
                if not is_cam_serial_setup:  # normal case, camera is wait for set and doesn't already exists
                    for attr, value in values.items():
                        setattr(objects, attr, value)
                    objects.save()
                else:  # weird case, new ip did not previously registered serial number
                    objects.delete()
                    values['ip'] = ip
                    is_cam_serial_setup.update(**values)
                client.update_camera = True
                client.save(update_fields=['update_camera', ])
                created = True
            else:
                if objects.active_automatic != values['active_automatic']:
                    # case only active automatic have changed
                    log_api.info(f'update active automatic {objects.active_automatic, values["active_automatic"]} ')
                    objects.active_automatic = values['active_automatic']
                    objects.save()
                    created = True  # this is the case where only active automatic is updated
        log_api.info(f'add camera in databases {objects, created} ')
        if created:
            modified = True
        for index_uri, uri_values in uri.items():
            log_api.info(f'add uri in databases {uri_values}  for index uri {index_uri}')
            objects_uri, created = CameraUri.objects.update_or_create(camera=objects, index_uri=index_uri,
                                                                      defaults=uri_values)
            log_api.info(f'uri is created {created}  \n\n')
            if created:
                modified = True
    log_api.info(f'values of modified camera is {modified} ')
    if modified:
        client.update_camera = True
    client.save(update_fields=['update_camera', ])
    return True


def _get_cam(client):
    cam = Camera.objects.filter(client=client)
    cam = cam.order_by('pk')
    log_api.info(f'request to get the cam of client  {client}')
    dict_cam = {key['ip']: key for key in list(cam.values())}
    uri_request = CameraUri.objects.filter(camera__client=client)
    dict_uri = {key['camera_id']: {} for key in list(uri_request.values())}
    for uri in list(uri_request.values()):
        dict_uri[uri['camera_id']][uri['index_uri']] = uri
    for ip, values in dict_cam.items():
        values['uri'] = dict_uri.get(values['id'], {})
        log_api.debug(f'---------------> get uri {values["id"]} ')
    return dict_cam


def _get_run_cam_active(client, cam_id):
    try:
        cam = Camera.objects.get(pk=cam_id, client=client, active=True, active_automatic=True)
        return cam
    except Camera.DoesNotExist:
        return False


def _get_cam_active(client):
    cam = CameraUri.objects.filter(camera__client=client, camera__active=True,
                                   camera__active_automatic=True).values(
        'camera_id', 'camera__on_camera_LD', 'camera__on_camera_HD').annotate(c=Count('camera_id'))
    log_api.info(f'request to get the active cam of client  {client}')
    cam_dict = {}
    for c in cam:
        cam_dict[c['camera_id']] = [c['camera__on_camera_LD'], c['camera__on_camera_HD']]
    return cam_dict


def _get_client(key, version=None):
    if version:
        try:
            client = Client.objects.select_related('machine_id').get(key=key)
            return client
        except Client.DoesNotExist:
            return False
    else:
        try:
            client = Client.objects.get(key=key)
            return client
        except Client.DoesNotExist:
            return False


def _update_timestamp(key):
    now = datetime.now(pytz.utc)
    Client.objects.filter(key=key).update(timestamp=now)
    log_api.debug(f' <<< updating client {key} timestamp >>> : {now}')
# -------------------------------------------------------------------------------------------------------


@csrf_exempt
async def ws_cam(socket):
    await socket.accept()
    log_api.info('accept socket')
    try:
        data = await socket.receive_json()
        client_rq = sync_to_async(_get_client, thread_sensitive=True)
        client = await client_rq(data['key'])
        if not client:
            await asyncio.sleep(60)
        else:
            log_api.debug(f'data is : {data}')
            cam = sync_to_async(_get_cam, thread_sensitive=True)
            result = await cam(client)
            log_api.debug(f'result of request : {result}')
            await socket.send_json(result)
            log_api.info(f'sending to client')
            client.update_camera = False
            async_save = sync_to_async(client.save)
            await async_save(update_fields=['update_camera', ])
    except (json.decoder.JSONDecodeError, AssertionError):
        await socket.close()


@csrf_exempt
async def ws_receive_cam(socket):
    await socket.accept()
    log_api.info('accept socket ws_receive_cam')
    try:
        data = await asyncio.wait_for(socket.receive_json(), timeout=1)
        client_rq = sync_to_async(_get_client, thread_sensitive=True)
        client = await client_rq(data['key'])
        if not client:
            await socket.close()
            await asyncio.sleep(60)
        else:
            log_api.info(f'key is : {data}')
            while True:
                cam = await socket.receive_json()
                log_api.info(f'receive cam : {cam} on socket')
                cam_up_rq = sync_to_async(_set_cam, thread_sensitive=True)
                await cam_up_rq(cam, client)
    except (json.decoder.JSONDecodeError, AssertionError, asyncio.TimeoutError) as ex:
        log_api.warning(f'exception in ws_received_cam : except-->{ex} / name-->{type(ex).__name__}')
        await socket.close()


@csrf_exempt
async def ws_send_cam(socket):
    await socket.accept()
    log_api.info('accept socket ws_send_cam')
    try:
        data = await asyncio.wait_for(socket.receive_json(), timeout=1)
        client_rq = sync_to_async(_get_client, thread_sensitive=True)
        client = await client_rq(data['key'])
        if not client:
            await socket.close()
            await asyncio.sleep(60)
        else:
            log_api.info(f'key is : {data}')
            while True:
                client = await client_rq(data['key'])
                if client.update_camera:
                    log_api.info(f'update on cam detected for client : {client}')
                    cam_rq = sync_to_async(_get_cam, thread_sensitive=True)
                    cam = await cam_rq(client)
                    await socket.send_json(cam)
                    data = await socket.receive_json()
                    if data['answer']:
                        client.update_camera = False
                        async_save = sync_to_async(client.save)
                        await async_save(update_fields=['update_camera', ])
                        break
                await asyncio.sleep(3)
            await socket.close()
    except (json.decoder.JSONDecodeError, AssertionError, asyncio.TimeoutError):
        await socket.close()


@csrf_exempt
async def ws_get_state(socket):
    await socket.accept()
    log_api.info('accept socket ws_get_state')
    try:
        data = await asyncio.wait_for(socket.receive_json(), timeout=1)
        version = data.get('version', None)
        client_rq = sync_to_async(_get_client, thread_sensitive=True)
        client = await client_rq(data['key'], version=version)
        if not client:
            await socket.close()
            await asyncio.sleep(60)
        else:
            log_api.info(f'key is : {data}')
            while True:
                log_api.debug(f' client state -->{socket._client_state} ')

                # This part is to check if the client is connected
                try:
                    response = {'ping': 1}
                    # security token for video
                    now = datetime.now(pytz.utc)
                    time_gap = now - client.token_video_time
                    time_from_last_token = time_gap.seconds
                    if time_from_last_token > 15 * 60:
                        await sync_to_async(_delete_space, thread_sensitive=True)(client)
                        token = secrets.token_urlsafe()
                        response['token1'] = token
                        response['token2'] = client.token_video
                        client.token_video_time = now
                        client.token_video = token
                        async_save = sync_to_async(client.save)
                        await async_save(update_fields=['token_video_time', 'token_video', ])
                    else:
                        response['token1'] = False
                    log_api.warning(f'before sending get state response {response}')
                    await socket.send_json(response)
                    log_api.warning(f'after sending get state response {response}')
                except ConnectionClosedError:
                    log_api.error(f'connection closed by client {client}')
                    await socket.close()
                timestamps_rq = sync_to_async(_update_timestamp, thread_sensitive=True)
                await timestamps_rq(data['key'])

                client = await client_rq(data['key'], version=version)
                log_api.warning(f'before client.change {client.change}')
                if version:  # retrocompatibility with no multi uuid
                    if client.machine_id.change:
                        response = {'reboot': client.machine_id.reboot,
                                    'tunnel_port': client.machine_id.tunnel_port,
                                    'docker_version': client.machine_id.docker_version, }
                        cam_rq = sync_to_async(_get_cam_active, thread_sensitive=True)
                        cam = await cam_rq(client)
                        response['cam'] = cam
                        log_api.warning(f'before sending json {response}')
                        await socket.send_json(response)
                        client.machine_id.change = False
                        async_save = sync_to_async(client.machine_id.save)
                        await async_save(update_fields=['change', ])
                else:  # retrocompatibility with client before 2.1
                    if client.change:
                        response = {'rec': client.rec, 'reboot': client.reboot, 'scan': client.scan,
                                    'tunnel_port': client.tunnel_port, 'docker_version': client.docker_version, }
                        cam_rq = sync_to_async(_get_cam_active, thread_sensitive=True)
                        cam = await cam_rq(client)
                        response['cam'] = cam
                        log_api.warning(f'before sending json {response}')
                        await socket.send_json(response)
                        client.change = False
                        async_save = sync_to_async(client.save)
                        await async_save(update_fields=['change', ])
                await asyncio.sleep(2)
    except (json.decoder.JSONDecodeError, AssertionError, asyncio.TimeoutError) as ex:
        log_api.warning(f'exception in socket ws_get_state : except-->{ex} / name-->{type(ex).__name__}')
        await socket.close()


@csrf_exempt
def init_conf(request):
    passwd = request.POST.get('pass', None)
    key = request.POST.get('key', None)
    version = request.POST.get('version', None)

    if key:  # client is settled, get the class_detected configuration
        client = Client.objects.filter(key=key)
        if client:
            class_detected = request.POST.get('class_detected', '["face", "person", "bicycle", "motorbike", "car",'
                                                                ' "truck", "cat", "dog"]')
            log_api.debug(f'getting the class : {class_detected} type {type(class_detected)}')
            if class_detected:
                list_class_detected = json.loads(class_detected)
                actual_stuffs = AlertStuffsChoice.objects.filter(client=client[0])
                list_actual_stuffs = [i[0] for i in list(actual_stuffs.values_list('stuffs'))]
                to_create = [s for s in list_class_detected if s not in list_actual_stuffs]
                for s in to_create:
                    new_stuffs, created = AlertStuffsChoice.objects.get_or_create(stuffs=s)
                    for cl in client:
                        new_stuffs.client.add(cl.id)
                for s in actual_stuffs.exclude(stuffs__in=list_class_detected):
                    for cl in client:
                        s.client.remove(cl)
            return JsonResponse(True, safe=False)
        else:
            return JsonResponse(False, safe=False)
    if passwd == settings.INIT_PASS:
        if version == '2':
            uuid = request.POST.get('machine', 'bad uuid')
            time.sleep(1)
            client = Client.objects.filter(machine_id__uuid=uuid)
            machine = MachineID.objects.filter(uuid=uuid)
            if client.exists():
                machine.update(reboot=False)
                log_api.info(f'CONF on machine   {machine} --> updated reboot {machine[0].reboot}')
                return JsonResponse({'clients': list(client.values('cp', 'city', 'key', 'scan', 'scan_camera',
                                                                   'video_authorize', 'automatic_launch_from_scan')),
                                     'machine': list(machine.values('tunnel_port', 'docker_version', 'reboot', ))},
                                    safe=False)
            else:
                try:
                    # obj, created = MachineID.update_or_create( uuid=uuid, default={date:now}
                    new_machine = MachineID(uuid=uuid)
                    new_machine.save()
                except IntegrityError:
                    pass
                return JsonResponse({'machine_id': True}, safe=False)
        else:  # retrocompatible with client 1.5
            uuid = request.POST.get('machine', 'bad uuid')
            time.sleep(1)
            client = Client.objects.filter(machine_id__uuid=uuid)
            if client.exists():
                client.update(reboot=False)
                # This is the default list class
                list_class_detected = json.loads('["face", "person", "bicycle", "motorcycle", "car",'
                                                 ' "truck", "cat", "dog"]')
                actual_stuffs = AlertStuffsChoice.objects.filter(client=client[0])
                list_actual_stuffs = [i[0] for i in list(actual_stuffs.values_list('stuffs'))]
                to_create = [s for s in list_class_detected if s not in list_actual_stuffs]
                for s in to_create:
                    new_stuffs, created = AlertStuffsChoice.objects.get_or_create(stuffs=s)
                    for cl in client:
                        new_stuffs.client.add(cl.id)
                for s in actual_stuffs.exclude(stuffs__in=list_class_detected):
                    for cl in client:
                        s.client.remove(cl)
                return JsonResponse(client.values('cp', 'city', 'key', 'tunnel_port', 'docker_version', 'reboot',
                                                  'scan_camera', 'scan')[0], safe=False)
            else:
                try:
                    # obj, created = MachineID.update_or_create( uuid=uuid, default={date:now}
                    new_machine = MachineID(uuid=uuid)
                    new_machine.save()
                except IntegrityError:
                    pass
                return JsonResponse({'machine_id': True}, safe=False)

    else:
        time.sleep(10)
        return JsonResponse({'statut': False}, safe=False)


# --------------------------SQL async request ------------------------------------------------------
def _set_result_ws(result, client):
    with transaction.atomic():
        result_db = Result(camera_id=result['cam'], file=client.folder + '/' + result['img'] + '.jpg',
                           brut=result['result_darknet'], correction=result['correction'],
                           video_time=datetime.fromisoformat(result['time_frame']), force_send=result['force_send'])
        result_db.save()
        log_api.debug(f'Saved result_db   {result_db}')
        list_objects = []
        for r in result['result_filtered']:
            log_api.debug(f'Saving object   {r}')
            list_objects.append(r[0])
            object_db = Object(result=result_db,
                               result_object=r[0],
                               result_prob=r[1],
                               result_loc1=r[2][0],
                               result_loc2=r[2][1],
                               result_loc3=r[2][2],
                               result_loc4=r[2][3])
            if len(r) > 3:
                object_db.result_option1 = r[3]
            object_db.save()
    # nb_obj = Counter([i for i in list_objects])
    # t = time.time()
    # check_result(result_db, nb_obj)
    # log_api.error(f'Result was checked for alert in {time.time()-t} seconds')
# --------------------------------------------------------------------------------------------------


@csrf_exempt
async def ws_run_cam_result(socket):
    await socket.accept()
    log_api.info('accept socket ws_cam result')
    try:
        data = await asyncio.wait_for(socket.receive_json(), timeout=1)
        client_rq = sync_to_async(_get_client, thread_sensitive=True)
        client = await client_rq(data['key'])
        if not client:
            await socket.close()
            await asyncio.sleep(60)
        else:
            log_api.info(f'key is : {data}')
            while True:
                result = await socket.receive_json()
                log_api.info(f'receive result : {result} on socket')
                await sync_to_async(_set_result_ws, thread_sensitive=True)(result, client)
    except (json.decoder.JSONDecodeError, AssertionError, asyncio.TimeoutError) as ex:
        log_api.warning(f'exception in ws_run_cam_result : except-->{ex} / name-->{type(ex).__name__}')
        await socket.close()


@csrf_exempt
async def ws_run_cam_img(socket):
    await socket.accept()
    log_api.info('accept socket ws_cam img')
    try:
        data = await asyncio.wait_for(socket.receive_json(), timeout=1)
        client_rq = sync_to_async(_get_client, thread_sensitive=True)
        client = await client_rq(data['key'])
        if not client:
            await socket.close()
            await asyncio.sleep(60)
        else:
            log_api.info(f'key is : {data}')
            while True:
                info_json = await socket.receive_json()
                log_api.debug(f'receive img name : {info_json} on socket')
                img = await socket.receive_bytes()
                log_api.debug(f'receive img with len : {len(img)} on socket')
                camera = await sync_to_async(Camera.objects.get, thread_sensitive=True)(pk=info_json['cam'])
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, process_img, img, info_json['name'], info_json['result'],
                                           client, camera)
    except (json.decoder.JSONDecodeError, AssertionError, asyncio.TimeoutError) as ex:
        log_api.warning(f'exception in ws_run_cam_img : except-->{ex} / name-->{type(ex).__name__}')
        await socket.close()


@csrf_exempt
async def ws_run_cam_img_real(socket):
    await socket.accept()
    log_api.info('accept socket ws_cam img real')
    try:
        data = await asyncio.wait_for(socket.receive_json(), timeout=1)
        client_rq = sync_to_async(_get_client, thread_sensitive=True)
        client = await client_rq(data['key'])
        if not client:
            await socket.close()
            await asyncio.sleep(60)
        else:
            log_api.info(f'key is : {data}')
            while True:
                info_json = await socket.receive_json()
                log_api.info(f'receive img name : {info_json} on socket')
                img = await socket.receive_bytes()
                log_api.info(f'receive img with len : {len(img)} on socket')
                camera = await sync_to_async(Camera.objects.get, thread_sensitive=True)(pk=info_json['cam'])
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, partial(process_img, img, info_json['name'], info_json['result'],
                                           client, camera, resize_factor=info_json['resize_factor'], real_time=True))
    except (json.decoder.JSONDecodeError, AssertionError, asyncio.TimeoutError) as ex:
        log_api.warning(f'exception in ws_run_cam_img : except-->{ex} / name-->{type(ex).__name__}')
        await socket.close()


def process_img(img, img_name, result_filtered, client, camera, resize_factor=1, real_time=False):
    img_path = settings.MEDIA_ROOT + '/' + client.folder + '/' + img_name
    os.makedirs(os.path.dirname(img_path), exist_ok=True)
    if not real_time:
        with open(img_path + '_no_box.jpg', 'wb') as file:
            file.write(img)
    img_pil = Image.open(BytesIO(img))
    draw = ImageDraw.Draw(img_pil)
    log_api.info(f'IMAGE >>> result filtered are   {result_filtered} size is {img_pil.size}')
    corner_list = []
    for r in result_filtered:
        outline = "green" if r[2][2] * r[2][3] > camera.max_object_area_detection else "red"
        box = ((int((r[2][0] - (r[2][2] / 2)) * resize_factor),
                int((r[2][1] - (r[2][3] / 2)) * resize_factor)),
               (int((r[2][0] + (r[2][2] / 2)) * resize_factor),
                int((r[2][1] + (r[2][3] / 2)) * resize_factor)))
        log_api.debug(f'IMAGE >>> box for {r} is {box}')
        draw.rectangle(box, outline=outline, width=int(3 * resize_factor) + 1)
        coordinate_for_writing = redress_coordinate(box[1], corner_list)
        corner_list.append(coordinate_for_writing)
        draw.text(coordinate_for_writing, r[0], fill=outline,
                  font=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                                          int(30 * resize_factor)))
    img_pil.save(img_path + '.jpg', "JPEG")
    log_api.info(f'saving image >>> {img_path}')


@csrf_exempt
async def ws_get_camera_state(socket):
    await socket.accept()
    log_api.info('accept socket ws_get_camera_state')
    try:
        data = await asyncio.wait_for(socket.receive_json(), timeout=1)
        client_rq = sync_to_async(_get_client, thread_sensitive=True)
        client = await client_rq(data['key'])
        if not client:
            await asyncio.sleep(60)
            await socket.close()
        else:
            log_api.info(f'key is : {data}')
            cam_rq = sync_to_async(_get_run_cam_active, thread_sensitive=True)
            first_connect = True
            while True:
                cam = await cam_rq(client, data['cam_id'])
                if cam:
                    if cam.change or first_connect:
                        log_api.info(f'cam change is {cam.change} first_connect is {first_connect}')
                        response = {'rec': cam.on_rec, 'on_camera_LD': cam.on_camera_LD, 'on_camera_HD': cam.on_camera_HD}
                        log_api.warning(f'before sending json {response}')
                        await socket.send_json(response)
                        cam.change = False
                        async_save = sync_to_async(cam.save)
                        await async_save(update_fields=['change', ])
                        first_connect = False
                    else:
                        await socket.send_json({'ping': 1})
                    await asyncio.sleep(2)
                else:
                    await socket.send_json({'ping': 1})
                    await asyncio.sleep(2)
    except (json.decoder.JSONDecodeError, AssertionError, asyncio.TimeoutError) as ex:
        log_api.warning(f'exception in socket ws_get_state : except-->{ex} / name-->{type(ex).__name__}')
        await socket.close()
