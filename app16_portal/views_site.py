from datetime import datetime

from django.conf import settings
from django.contrib.auth import login
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponse
from django.shortcuts import redirect
from django.views.decorators.csrf import csrf_exempt

from app16_portal.models import Key, Site
from app16_portal.utils import encode_data, decode_data, sign_data, verify_signature
from app4_ehpad_base.api_netsoins import create_username


def decode(data: dict):
    return decode_data(bytes(data.get('data'), 'UTF-8'))


def get_site_infos():
    result = {}
    try:
        result['logo'] = settings.IMG_LOGO
    except AttributeError:
        pass
    try:
        result['facebook'] = settings.FACEBOOK
    except AttributeError:
        pass
    try:
        result['main_site'] = settings.SITE_INTERNET
    except AttributeError:
        pass
    return result


def site_infos(request):
    if request.method == 'GET':
        signed_infos = sign_data(get_site_infos(), Key.objects.get(is_local=True, is_public=False).key_bytes())
        return HttpResponse(encode_data(signed_infos))


def public_key(request):
    if request.method == 'GET':
        infos = get_site_infos()
        infos['key'] = Key.objects.get(is_local=True, is_public=True).key
        return HttpResponse(encode_data(infos))


def update_user(user, data):
    try:
        birth_date = data.pop('birth_date')
        user.profileserenicia.birth_date = datetime.fromisoformat(birth_date)
    except KeyError:
        pass
    for key, value in data.items():
        setattr(user, key, value or None)
        setattr(user.profile, key, value or None)
        setattr(user.profileserenicia, key, value or None)
    user.save()
    user.profile.save()
    user.profileserenicia.save()


def get_unique_username(last_name, first_name):
    username = create_username(last_name=last_name, first_name=first_name)
    users_nb = User.objects.filter(username=username).count()
    if users_nb > 0:
        username += str(users_nb + 1)
    return username


@csrf_exempt
def add_portal_user(request):
    if request.POST.get('data'):
        decoded_data = decode(request.POST)
        data = verify_signature(decoded_data, Site.objects.get(name='portal').public_key.key_bytes())
        if User.objects.filter(email=data.get('email')).exists():
            user = User.objects.get(email=data.get('email'))
        elif User.objects.filter(last_name__iexact=data.get('last_name'),
                                 first_name__iexact=data.get('first_name')).count == 1:
            user = User.objects.get(last_name__iexact=data.get('last_name'), first_name__iexact=data.get('first_name'))
        else:
            username = get_unique_username(data.get('last_name'), data.get('first_name'))
            user = User.objects.create(username=username)
        update_user(user, data)
        return HttpResponse()


@csrf_exempt
def update_portal_user(request):
    if request.POST.get('data'):
        decoded_data = decode(request.POST)
        data = verify_signature(decoded_data, Site.objects.get(name='portal').public_key.key_bytes())
        try:
            user = User.objects.get(profile__portal_token=data.get('portal_token'))
            update_user(user, data)
            return HttpResponse()
        except ObjectDoesNotExist:
            pass


@csrf_exempt
def login_from_portal(request):
    if request.POST.get('data'):
        decoded_data = decode(request.POST)
        if decoded_data.get('signed'):
            data = verify_signature(decoded_data, Site.objects.get(name='portal').public_key.key_bytes())
            try:
                user = User.objects.get(profile__portal_token=data.get('token'))
            except ObjectDoesNotExist:
                return redirect('login')
            user.backend = 'django.contrib.auth.backends.ModelBackend'
            login(request, user)
            return redirect('app4_ehpad_base index')


@csrf_exempt
def add_portal_key(request):
    if request.POST.get('data'):
        decoded_data = decode(request.POST)
        if decoded_data.get('key'):
            key = Key.objects.create(key=decoded_data.get('key'))
            Site.objects.create(name='portal', url=settings.PORTAL_URL, public_key=key, is_linked=True)
            return HttpResponse()
