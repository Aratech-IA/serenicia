import logging
import shutil

from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
import os
import base64
from django.conf import settings

from app1_base.models import Profile
from app1_base.log import Logger
from app4_ehpad_base.models import ProfileSerenicia
from app7_video.extract_pict import extract_picture
from pathlib import Path

logger = Logger("websucks", level=logging.ERROR).run()


@csrf_exempt
def index(request, myvideo):
    if request.method == 'POST':
        video_binary_string = request.POST.get('vdo_rec')
        decoded_string = base64.b64decode(video_binary_string)
        filename = request.POST.get('filename')
        logger.info(f'filename: {filename}')
        path = settings.MEDIA_ROOT + '/temp/'
        path2 = settings.MEDIA_ROOT + '/videos_users/' + filename + '/'
        logger.info(f'path: {path}')
        try:
            Path(path).mkdir(parents=True, exist_ok=True)
            Path(path2).mkdir(parents=True, exist_ok=True)
            path_video = path + filename + '.mp4'
            path2_video = path2 + filename + '.mp4'
            if os.makedirs(os.path.dirname(path_video), exist_ok=True):
                shutil.rmtree(path_video)
                os.makedirs(os.path.dirname(path_video))
            with open(path_video, 'wb') as wfile:
                wfile.write(decoded_string)
            extract_picture(path_video, filename)
            Profile.objects.filter(user__profileserenicia__folder=filename).update(video_ready=True)
            shutil.move(path_video, path2_video)
            # os.remove(path_video)
            return JsonResponse('POST', safe=False)
            # return redirect('app4_ehpad_base index')
        except Exception as prob:
            logger.info(f'cken: {prob}')
    folder = request.user.profileserenicia.folder
    if request.user.has_perm('app0_access.view_registerfacereco') and myvideo == 'false':
        try:
            folder = ProfileSerenicia.objects.get(user__id=request.session['resident_id']).folder
        except KeyError:
            pass
    return render(request, 'app7_video/index.html', {'folder': folder})
