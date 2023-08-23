from django.conf import settings
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.models import Permission, Group, User
from django.core.exceptions import ObjectDoesNotExist
from django.core.paginator import Paginator
from django.db.models import Q
from django.db.models.functions import Lower
from django.http import FileResponse
from django.shortcuts import render, redirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from app0_access.forms import UserTypeForm
from app0_access.models import ACCESS_DESCRIPTIONS, RELATED_PERMISSIONS, USER_TYPE

if settings.DOMAIN.lower() == 'serenicia':
    from app5_ehpad_messaging.models import TempAssignation


@login_required
@permission_required('app0_access.view_rightsmanagement')
def index(request):
    try:
        request.session.pop('resident_id')
    except KeyError:
        pass
    return render(request, 'app0_access/index.html')


def get_app_list():
    result = []
    for app in ACCESS_DESCRIPTIONS.keys():
        tmp_dict = ACCESS_DESCRIPTIONS[app]
        tmp_dict['code'] = app
        if RELATED_PERMISSIONS.get(app):
            tmp_dict['option'] = RELATED_PERMISSIONS[app]['description']
        result.append(tmp_dict)
    return sorted(result, key=lambda key: key['app_name'])


def get_list_related_permissions(codename):
    result = []
    try:
        for perm in RELATED_PERMISSIONS[codename]['perms']:
            label = perm['app_label']
            for model in perm['models']:
                codes = [f'view_{model}', f'add_{model}', f'delete_{model}', f'change_{model}']
                result.extend(list(Permission.objects.filter(content_type__app_label=label,
                                                             codename__in=codes)))
    except KeyError:
        pass
    return result


@login_required
@permission_required('app0_access.view_rightsmanagement')
def new_group(request):
    context = {}
    if request.method == 'POST':
        if Group.objects.filter(name=request.POST.get('group-name')).exists():
            context.update({'category': _('Cannot save'), 'message': _('A group with this name already exists')})
        else:
            grp = Group.objects.create(name=request.POST.get('group-name'))
            result = list(Permission.objects.filter(codename__in=request.POST.getlist('code'),
                                                    content_type__app_label='app0_access'))
            for option in request.POST.getlist('option'):
                result.extend(get_list_related_permissions(option.split('.')[0]))
            grp.permissions.set(result)
            context.update({'category': _('Saved'), 'message': _('The group has been saved')})
            return redirect('select rights group')
    context.update({'apps': get_app_list(), 'user_type': USER_TYPE})
    return render(request, 'app0_access/new_group.html', context)


@login_required
@permission_required('app0_access.view_rightsmanagement')
def select_group(request):
    list_grp = []
    for grp in Group.objects.order_by(Lower('name')).exclude(permissions__codename='view_prospect'):
        list_grp.append({'grp': grp, 'users': User.objects.filter(groups=grp).count()})
    paginator = Paginator(list_grp, 25)  # Show 25 groups per page.
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'app0_access/select_group.html', {'page_obj': page_obj})


def get_user_type_codename(permissions):
    for codename in USER_TYPE.keys():
        if permissions.filter(codename=codename):
            return codename
    return False


@login_required
@permission_required('app0_access.view_rightsmanagement')
def modify_group(request, grp_id):
    try:
        grp = Group.objects.get(id=grp_id)
    except ObjectDoesNotExist:
        return redirect('select rights group')

    users = User.objects.filter(groups=grp)
    users_count = users.count()
    users_active = users.filter(is_active=True).order_by('last_name', 'first_name')
    users_inactive = users.filter(is_active=False).order_by('last_name', 'first_name')

    users_family_actifs_without_resident = []
    users_family_actifs_with_resident_inactif = []
    # get more info when user is family
    if grp.permissions.filter(codename='view_family').exists():
        users_family_actifs_without_resident = User.objects.filter(
            groups=grp, profileserenicia__user_list__isnull=True, is_active=True).order_by('last_name', 'first_name')
        active_residents = User.objects.filter(groups__permissions__codename__in=['view_residentehpad'], is_active=True)
        inactive_residents = User.objects.filter(groups__permissions__codename__in=['view_residentehpad'], is_active=False)
        users_family_actifs_with_resident_inactif = User.objects.filter(
            groups=grp, profileserenicia__user_list__isnull=False, is_active=True,
            profileserenicia__user_list__user__id__in=inactive_residents).order_by('last_name', 'first_name')
        users_active = User.objects.filter(
            groups=grp, profileserenicia__user_list__isnull=False, is_active=True,
            profileserenicia__user_list__user__id__in=active_residents).order_by('last_name', 'first_name')

    context = {'list_users': [{'users': users_active, 'fill': 'green'},
                              {'users': users_family_actifs_with_resident_inactif,
                               'fill': 'blue'},
                              {'users': users_family_actifs_without_resident,
                               'fill': 'orange'},
                              {'users': users_inactive, 'fill': 'red'},
                              ],
               'nb_users': users_count}

    if request.method == 'POST':
        if request.POST.get('delete'):
            Group.objects.filter(id=grp.id).delete()
            return redirect('select rights group')
        else:
            if request.POST.get('group-name') != grp.name:
                grp.name = request.POST.get('group-name')
                grp.save()
            result = list(Permission.objects.filter(codename__in=request.POST.getlist('code'),
                                                    content_type__app_label='app0_access'))
            if request.POST.get('user_type'):
                result.append(Permission.objects.get(codename=request.POST.get('user_type')))
            for option in request.POST.getlist('option'):
                result.extend(get_list_related_permissions(option.split('.')[0]))
            grp.permissions.set(result)
            context.update({'category': _('Saved'), 'message': _('Changes have been saved')})
    apps = get_app_list()
    for app in apps:
        selected, option = False, False
        if grp.permissions.filter(codename=app['code']):
            selected = True
            perms = get_list_related_permissions(app['code'])
            for perm in perms:
                if grp.permissions.filter(id=perm.id):
                    option = True
        apps[apps.index(app)].update({'selected': selected, 'option_selected': option})
    user_type = get_user_type_codename(grp.permissions.all())
    if user_type:
        type_form = UserTypeForm(initial={'user_type': user_type})
    else:
        type_form = UserTypeForm()
    context.update({'type_form': type_form, 'apps': apps, 'grp': grp})
    return render(request, 'app0_access/modify_group.html', context)


@login_required
@permission_required('app0_access.view_rightsmanagement')
def select_user(request, grp_id):
    users = User.objects.exclude(groups__permissions__codename='view_prospect').order_by(Lower('last_name'),
                                                                                         Lower('first_name'))
    context = {'groups': Group.objects.exclude(permissions__codename='view_prospect').order_by(Lower('name'))}
    if request.POST.get('search'):
        search = request.POST.get('search')
        users = users.filter(Q(last_name__icontains=search) | Q(first_name__icontains=search))
        context['searching'] = search
    if grp_id:
        users = users.filter(groups__id=grp_id)
        context['selected_grp'] = grp_id
    paginator = Paginator(users, 25)  # Show 25 users per page.
    context['page_obj'] = paginator.get_page(request.GET.get('page'))
    return render(request, 'app0_access/select_user.html', context)


@login_required
@permission_required('app0_access.view_rightsmanagement')
def modify_user(request, user_id):
    try:
        user = User.objects.get(id=user_id)
    except ObjectDoesNotExist:
        return redirect(request.META.get('HTTP_REFERER'))
    groups = Group.objects.order_by(Lower('name')).exclude(permissions__codename='view_prospect')
    context = {'groups': groups}
    if request.method == 'POST':
        if request.POST.get('choice'):
            resident = User.objects.get(id=request.POST.get('choice'))
            user.profileserenicia.user_list.add(resident.profile)
            TempAssignation.objects.filter(demander=user).delete()
            message = _('The resident has been successfully associated with this user')
        elif request.POST.get('active'):
            if int(request.POST.get('active')):
                user.is_active = True
                message = _('This user now has access to the Serenicia site')
            else:
                user.is_active = False
                message = _('This user no longer has access to the Serenicia site')
            user.save()
        else:
            user.groups.set(groups.filter(id=request.POST.get('group')))
            message = _('This user is now part of the group') + ' : ' + user.groups.get().name
        context.update({'category': _('Saved'), 'message': message})
        context['redirect'] = reverse('select user', kwargs={'grp_id': 0})
    context['selected_user'] = user
    if user.groups.filter(permissions__codename='view_family').exists():
        residents = user.profileserenicia.user_list.filter(user__groups__permissions__codename='view_residentehpad')
        if not residents.exists():
            try:
                tmp = TempAssignation.objects.get(demander=user)
                context['tmp_assign'] = tmp
                residents = User.objects.filter(last_name__iexact=tmp.last_name, first_name__iexact=tmp.first_name,
                                                profile__client__isnull=False,
                                                groups__permissions__codename='view_residentehpad')
            except ObjectDoesNotExist:
                pass
        context['residents'] = residents
    return render(request, 'app0_access/modify_user.html', context)


@login_required
@permission_required('app0_access.view_rightsmanagement')
def select_group_by_permission(request):
    if not request.user.profile.advanced_user:
        return redirect('access index')
    apps = get_app_list()
    for app in apps:
        group = Group.objects.filter(permissions__codename=app['code'])
        app['groups'] = sorted(group, key=lambda key: key.name.lower())
        if app.get('option'):
            group = group.filter(permissions__in=get_list_related_permissions(app['code'])).distinct('id')
            app['groups_option'] = sorted(group, key=lambda key: key.name.lower())
    return render(request, 'app0_access/select_group_by_permission.html', {'apps': apps})


@login_required
@permission_required('app0_access.view_rightsmanagement')
def user_types(request):
    if not request.user.profile.advanced_user:
        return redirect('access index')
    result = []
    list_types = USER_TYPE
    context = {'user_types': list_types, 'force_display': None}
    if request.POST.get('user_type'):
        try:
            group = Group.objects.get(id=request.POST.get('group'))
            group.permissions.set(group.permissions.exclude(codename__in=list_types.keys()))
            if request.POST.get('user_type') != 'none':
                group.permissions.add(Permission.objects.get(codename=request.POST.get('user_type'),
                                                             content_type__app_label='app0_access'))
                context['force_display'] = request.POST.get('user_type')
            else:
                context['force_display'] = 'none'
        except ObjectDoesNotExist:
            pass
    for codename, name in list_types.items():
        tmp_dict = {'name': name,
                    'groups': Group.objects.filter(permissions__codename=codename).order_by(Lower('name')),
                    'codename': codename}
        result.append(tmp_dict)
    result = sorted(result, key=lambda key: key['name'])
    result.insert(0, {'name': _('Not defined'),
                      'groups': Group.objects.exclude(permissions__codename__in=list_types.keys()).order_by(
                          Lower('name')),
                      'codename': 'none'})
    context['list_types'] = result
    return render(request, 'app0_access/user_types.html', context)
