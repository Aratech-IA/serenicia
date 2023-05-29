import logging

from django.conf import settings
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from datetime import datetime
from django.utils.translation import gettext_lazy as _

import glob
from app1_base.log import Logger
from app1_base.models import Profile
from app4_ehpad_base.models import ProfileSerenicia
# Event
from app4_ehpad_base.views_cuisine_eval import display_meal, evaluate_entree, evaluate_main_dish, evaluate_dessert, \
    finalize_evaluation
from app4_ehpad_base.views import show_images_hd, get_data_photo_album

from django.http import HttpResponse, JsonResponse

if 'log_app4' not in globals():
    log_app13 = Logger('app13_resident', level=logging.ERROR, file=False).run()


def cleaning_meal_data(meal_data):
    # décide si on affiche un repas du midi (noon) ou du soir (evening)
    if datetime.now().hour < 16:
        daytime = 'noon'
    else:
        daytime = 'evening'
    for menu in meal_data['meal_list']:
        # supprime les repas qui ne sont pas du jour
        if menu.date != meal_data['today']:
            meal_data['meal_list'].remove(menu)
        elif menu.type != daytime:
            meal_data['meal_list'].remove(menu)


def index(request):
    request.session['resident_id'] = request.user.id
    ws_alexa = 'wss://' + request.get_host() + ':' + request.META.get('SERVER_PORT') + '/ws_alexa/'
    meal_data = display_meal(request.user.id)
    log_app4.debug(f'app13  >>> user id is {request.user.id} ')
    resident_folder = User.objects.get(pk=request.user.id).profileserenicia.folder
    carousel_images = show_images_hd(resident_folder)
    page_resident = True
    cleaning_meal_data(meal_data)

    # récupère les évènements du jour pour le résident connecté
    # todays_event = Event.objects.filter(participants__user=request.user,
    #                                        start__date=datetime.now().date()).order_by('start')
    context = {**meal_data, **carousel_images, 'todays_event': '', 'page_resident': page_resident,
               'ws_alexa': ws_alexa}

    return render(request, 'app13_resident/index.html', context)


def menus(request):
    request.session['resident_id'] = request.user.id
    meal_data = display_meal(request.user.id)
    page_menus = True

    ws_alexa = 'wss://' + request.get_host() + ':' + request.META.get('SERVER_PORT') + '/ws_alexa/'
    context = {**meal_data, 'page_menus': page_menus, 'ws_alexa': ws_alexa}

    return render(request, 'app13_resident/menus.html', context)


def menus_entree(request, evaltype='manual'):
    ws_alexa = 'wss://' + request.get_host() + ':' + request.META.get('SERVER_PORT') + '/ws_alexa/'
    return evaluate_entree(request, ws_alexa=ws_alexa, evaltype=evaltype, template='app13_resident/eval_entree.html',
                           redir_url='app13_resident eval main dish')


def menus_main_dish(request, evaltype='manual'):
    ws_alexa = 'wss://' + request.get_host() + ':' + request.META.get('SERVER_PORT') + '/ws_alexa/'
    return evaluate_main_dish(request, ws_alexa=ws_alexa, evaltype=evaltype, template='app13_resident/eval_maindish.html',
                              redir_url='app13_resident eval dessert')


def menus_dessert(request, evaltype='manual'):
    ws_alexa = 'wss://' + request.get_host() + ':' + request.META.get('SERVER_PORT') + '/ws_alexa/'
    return evaluate_dessert(request, ws_alexa=ws_alexa, evaltype=evaltype, template='app13_resident/eval_dessert.html',
                            redir_url='app13_resident eval finalize')


def menus_finalize(request, evaltype='manual'):
    ws_alexa = 'wss://' + request.get_host() + ':' + request.META.get('SERVER_PORT') + '/ws_alexa/'
    return finalize_evaluation(request, ws_alexa=ws_alexa, evaltype=evaltype, template='app13_resident/eval_finalize.html',
                               redir_url='app13_resident index')


@login_required
def videochat(request):
    """display a jitsi conference configured with the user name and the selected roomname"""
    username = request.user.first_name + " " + request.user.last_name
    ws_alexa = 'wss://' + request.get_host() + ':' + request.META.get('SERVER_PORT') + '/ws_alexa/'
    context = {'username': username, 'ws_alexa': ws_alexa}
    resident = User.objects.get(pk=request.session['resident_id'])  # resident identification
    context['roomname'] = resident.first_name.lower() + resident.last_name.lower() + str(
        resident.profileserenicia.token_video_call)
    return render(request, 'app13_resident/videochat.html', context)


def auth(request, token):
    try:
        user = User.objects.get(profile__client__key=token)
        login(request, user, backend='django.contrib.auth.backends.ModelBackend')
        return redirect('app13_resident index')
    except ObjectDoesNotExist:
        return HttpResponse(_('No user has been affected to this room yet.'))
    except MultipleObjectsReturned:
        return HttpResponse(_('Multiple user connected, check the admin configuration.'))


def test(request):
    request.session['resident_id'] = request.user.id
    ws_alexa = 'wss://' + request.get_host() + ':' + request.META.get('SERVER_PORT') + '/ws_alexa/'
    resident_folder = User.objects.get(pk=request.user.id).profileserenicia.folder
    meal_data = display_meal(request.user.id)
    carousel_images = show_images_hd(resident_folder)
    page_resident = True
    time = datetime.now().hour
    if time < 12:
        greetings = 'Bonjour'
    elif time == 12:
        greetings = 'Bon Appetit'
    elif 12 < time < 18:
        greetings = 'Bon après-midi'
    elif 18 < time < 21:
        greetings = 'Bonsoir'
    else:
        greetings = 'Bonne nuit'

    cleaning_meal_data(meal_data)
    # todays_event = Event.objects.filter(participants__user=request.user,
    #                                        start__date=datetime.now().date()).order_by('start')
    context = {'today': datetime.now().date(), 'greet': greetings, 'notation': meal_data['notation'],
               **carousel_images, 'todays_event': '', 'page_resident': page_resident, 'ws_alexa': ws_alexa}
    try:
        context['meal'] = meal_data['meal_list'][0]
    except IndexError:
        pass
    return render(request, 'app13_resident/test.html', context)


def list_albums_photo(request):
    request.session['resident_id'] = request.user.id
    ws_alexa = 'wss://' + request.get_host() + ':' + request.META.get('SERVER_PORT') + '/ws_alexa/'
    resident = User.objects.get(pk=request.session['resident_id'])
    folder = resident.profileserenicia.folder
    result = get_data_photo_album(folder)

    context = {'ws_alexa': ws_alexa, 'photo_album': result}
    return render(request, 'app13_resident/list_album_photo.html', context)


def photo_from_album(request, name):
    resident = ProfileSerenicia.objects.get(user__pk=request.session['resident_id'])
    ws_alexa = 'wss://' + request.get_host() + ':' + request.META.get('SERVER_PORT') + '/ws_alexa/'
    base_dir = settings.MEDIA_ROOT + '/residents/' + resident.folder + '/photo_family/'
    base_url = settings.MEDIA_URL + 'residents/' + resident.folder + '/photo_family/' + name + '/'
    list_pictures = [base_url + path.split('/')[-1] for path in glob.glob(base_dir + name + '/*.*')]
    list_pictures.sort(reverse=True)
    context = {'list_pictures': list_pictures, 'ws_alexa': ws_alexa}
    return render(request, 'app13_resident/gallery_in_album.html', context)


def get_contact_for_call(request):
    ws_alexa = 'wss://' + request.get_host() + ':' + request.META.get('SERVER_PORT') + '/ws_alexa/'
    profile = Profile.objects.get(user__pk=request.session['resident_id'])
    contact = ProfileSerenicia.objects.filter(user_list=profile, user__groups__permissions__codename='view_family')
    context = {'ws_alexa': ws_alexa, 'list_contact': contact}
    return render(request, 'app13_resident/contact_for_video_call.html', context)


def interventions(request):
    ws_alexa = 'wss://' + request.get_host() + ':' + request.META.get('SERVER_PORT') + '/ws_alexa/'
    return render(request, 'app13_resident/interventions.html', context={'ws_alexa': ws_alexa})
