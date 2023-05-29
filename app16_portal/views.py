from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.db.models.functions import Lower
from django.forms import model_to_dict
from django.shortcuts import render, redirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from app16_portal.models import Site, PortalProfile, Key
from app16_portal.utils import get_response, post_message, encode_data

TIMEOUT_GET = 0.5
TIMEOUT_POST = 2


def login_page(request):
    if request.user.is_authenticated:
        return redirect('portal index')
    template_name = 'app16_portal/login.html'
    if request.method == 'POST':
        username = request.POST.get('username')
        try:
            User.objects.get(username=username)
        except ObjectDoesNotExist:
            return render(request, template_name, {'error': _("This username doesn't exist")})
        user = authenticate(request, username=username, password=request.POST.get('password'))
        if user is not None:
            login(request, user)
            return redirect('portal index')
        else:
            return render(request, template_name, {'error': _('Wrong password'), 'username': username})
    return render(request, template_name)


def send_user_infos(user, site):
    data = {'last_name': user.last_name, 'first_name': user.first_name, 'email': user.email,
            'portal_token': user.portalprofile.key, 'phone_number': user.profile.phone_number or '',
            'civility': user.profile.civility or '', 'adress': user.profile.adress or '', 'cp': user.profile.cp or '',
            'city': user.profile.city or '', 'birth_date': user.profileserenicia.birth_date.isoformat() or ''}
    is_sent = post_message(site.url + reverse('add portal user'), TIMEOUT_POST, data,
                           Key.objects.get(is_local=True, is_public=False).key_bytes())
    if is_sent:
        user.portalprofile.linked_sites.add(site)


@login_required
def index(request):
    try:
        request.user.portalprofile
    except ObjectDoesNotExist:
        PortalProfile(user_ptr=request.user).save_base(raw=True)
    context = {'token_data': encode_data({'token': request.user.portalprofile.key})}
    if request.POST.get('link'):
        try:
            send_user_infos(request.user, request.user.portalprofile.linked_sites.get(id=request.POST.get('link')))
            return redirect('portal index')
        except ObjectDoesNotExist:
            pass
    result = []
    for site in Site.objects.filter(group=request.user.portalprofile.site_group).order_by(Lower('name')):
        data = model_to_dict(site)
        received = get_response(site.url + reverse('get site infos'), TIMEOUT_GET, site.public_key.key_bytes())
        if received:
            data.update(received)
            Site.objects.filter(id=site.id).update(facebook=data.get('facebook'), main_site=data.get('main_site'))
        result.append(data)
    context['sites'] = result
    return render(request, 'app16_portal/index.html', context)


def logout_page(request):
    logout(request)
    return redirect('portal login')
