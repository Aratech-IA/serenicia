from django.shortcuts import render
from django.utils.translation import gettext as _
from app4_ehpad_base.models import ProfileSerenicia, UserListIntermediate


def resident_employee(access, actif=True):
    caregivers = ProfileSerenicia.objects.filter(user__groups__permissions__codename=access).filter(
        user__is_active=True).exclude(user__last_login__isnull=True).order_by('user__last_name')
    dict_relation = {}
    for caregiver in caregivers:
        residents = caregiver.user_list.filter(user__groups__permissions__codename="view_residentehpad",
                                               user__is_active=actif).order_by(
            'user__profile__client__room_number')
        dict_relation[caregiver] = residents
    return dict_relation


def resident_employee_manual(access, up=False, actif=True):
    caregivers = ProfileSerenicia.objects.filter(
        user__groups__permissions__codename=access, user__is_active=True, UP_volunteer=up).exclude(
        user__last_login__isnull=True).order_by('user__last_name')
    dict_relation = {}
    for caregiver in caregivers:
        list_manual_resident = UserListIntermediate.objects.filter(
            profileserenicia=caregiver, profile__user__is_active=actif,
            was_manual=True).values_list("profile", flat=True)
        residents = caregiver.user_list.filter(user__groups__permissions__codename="view_residentehpad",
                                               id__in=list_manual_resident).order_by(
            'user__profile__client__room_number')
        dict_relation[caregiver] = residents
    return dict_relation


def resident_employee_automatic(access, actif=True):
    caregivers = ProfileSerenicia.objects.filter(user__groups__permissions__codename=access).filter(
        user__is_active=True).exclude(user__last_login__isnull=True).order_by('user__last_name')
    list_manual_resident = UserListIntermediate.objects.filter(
        profileserenicia__user__groups__permissions__codename=access,
        was_manual=True).values_list("profile", flat=True)
    dict_relation = {}
    for caregiver in caregivers:
        residents = caregiver.user_list.filter(user__groups__permissions__codename="view_residentehpad",
                                               user__is_active=actif).exclude(
            id__in=list_manual_resident).order_by(
            'user__profile__client__room_number')
        dict_relation[caregiver] = residents
    return dict_relation


def table_relations(request):
    accesss = []
    relations = []

    access_labels = {
        '-------': _('Choose a function to see the relationships'),
        'view_as': _('Relationships Caregiver'),
        'view_ash': _('Relationships Hospital Caregiver'),
        'view_ide': _('Relationships Nursing'),
    }

    try:
        request.session.pop('resident_id')
    except KeyError:
        pass

    accesss = list(access_labels.keys())
    access = '-------'

    if request.POST:
        access = request.POST.get("access")
        dict_relation = resident_employee(access)
        relations = [(key.user, [x.user for x in value]) for key, value in dict_relation.items()]

    context = {"rels": relations, "accesss": accesss, "access": access, "access_labels": access_labels}

    return render(request, 'app6_care/rela_table/rela_table.html', context)

