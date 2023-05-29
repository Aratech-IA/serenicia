import os
import sys


# Because this script have to be run in a separate process from manage.py
# you need to set up a Django environnement to use the Class defined in
# the Django models. It is necesssary to interact witht the Django database
# ------------------------------------------------------------------------------
# to get the projet.settings it is necessary to add the parent directory
# to the python path


def install_app14():
    try:
        sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    except NameError:
        sys.path.append(os.path.abspath('../..'))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "projet.settings.settings")
    import django

    django.setup()

    # script initialisation droits, groupes
    from django.contrib.auth.models import Group, Permission
    from app12_delivery.models import DeliveryDay

    g1 = Group.objects.get_or_create(name="Customer Delivery")
    g2 = Group.objects.get_or_create(name="Delivery Man")
    g3 = Group.objects.get_or_create(name="Delivery Business")
    g1[0].save()
    g2[0].save()
    g3[0].save()
    p_g1 = Permission.objects.get(content_type__app_label="access", name="Can view customer delivery")
    p_g2 = Permission.objects.get(content_type__app_label="access", name="Can view delivery")
    p_g3 = Permission.objects.get(content_type__app_label="access", name="Can view delivery business")
    g1[0].permissions.add(p_g1)
    g2[0].permissions.add(p_g2)
    g3[0].permissions.add(p_g3)
    print(f'-- create Group {g2[0]} with perm : {p_g2} \n'
          f'-- create Group {g1[0]} with perm : {p_g1} \n'
          f'-- create Group {g3[0]} with perm : {p_g3}')
    if enumerate(DeliveryDay.objects.all()) != 0:
        DeliveryDay.objects.create()
        print("week register")
    else:
        print("week already register")


install_app14()
