import os
import sys

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

from crontab import CronTab
from django.conf import settings


def auto_ordering_tour():
    cron = CronTab(user=True)
    if not any(cron.find_command('cron_tour_auto.py')):
        cmd = "cd " + settings.BASE_DIR + " && "
        cmd += settings.PYTHON + ' ' + os.path.join(settings.BASE_DIR, 'app12_delivery/batch/cron_tour_auto.py')
        job = cron.new(command=cmd)
        job.hours.on(21)
        cron.write()


def install_app14_cron():
    cmd = "cd " + settings.BASE_DIR + " && "
    cmd += settings.PYTHON + ' ' + os.path.join(settings.BASE_DIR, 'app12_delivery/batch/install_app14.py')
    os.system(cmd)


install_app14_cron()
