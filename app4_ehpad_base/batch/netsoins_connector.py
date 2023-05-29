import sys
import os

# Because this script have to be run in a separate process from manage.py
# you need to set up a Django environnement to use the Class defined in
# the Django models. It is necesssary to interact witht the Django database
# ------------------------------------------------------------------------------
# to get the projet.settings it is necessary to add the parent directory
# to the python path


try:
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
except NameError:
    sys.path.append(os.path.abspath('../..'))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "projet.settings.settings")
import django

django.setup()

from app4_ehpad_base.api_netsoins import cron_netsoins_resident, cron_netsoins_staff, cron_netsoins_family, \
    update_staff_permissions, cron_post_all_cards

if __name__ == '__main__':
    cron_netsoins_resident()
    cron_netsoins_staff()
    cron_netsoins_family()
    update_staff_permissions()
    #cron_post_all_cards()
