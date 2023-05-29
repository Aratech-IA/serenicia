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

from app5_ehpad_messaging.batch import install_cron as app5cron


def install_pics_counter_cron():
    cron = CronTab(user=True)
    if not any(cron.find_command('pics_counter.py')):
        cmd = "cd " + settings.BASE_DIR + " && "
        cmd += settings.PYTHON + ' ' + os.path.join(settings.BASE_DIR, 'app4_ehpad_base/batch/pics_counter.py')
        cmd += " > " + settings.BASE_DIR + "/log/pics_counter.log 2>&1&"
        job = cron.new(command=cmd)
        job.hours.on(11, 16, 22)
        cron.write()


def install_thumbnails_cron():
    cron = CronTab(user=True)
    if not any(cron.find_command('thumbnails.py')):
        cmd = "cd " + settings.BASE_DIR + " && "
        cmd += settings.PYTHON + ' ' + os.path.join(settings.BASE_DIR, 'app4_ehpad_base/batch/thumbnails.py')
        cmd += " > " + settings.BASE_DIR + "/log/thumbnails.log 2>&1&"
        job = cron.new(command=cmd)
        job.hours.on(11, 16, 22)
        cron.write()


def install_api_netsoins_cron():
    cron = CronTab(user=True)
    if not any(cron.find_command('netsoins_connector.py')):
        cmd = "cd " + settings.BASE_DIR + " && "
        cmd += settings.PYTHON + ' ' + os.path.join(settings.BASE_DIR, 'app4_ehpad_base/batch/netsoins_connector.py')
        cmd += " > " + settings.BASE_DIR + "/log/netsoins_connector.log 2>&1&"
        job = cron.new(command=cmd)
        # run every minutes
        job.every(5).minutes()
        cron.write()


def install_create_calendar():
    cron = CronTab(user=True)
    if not any(cron.find_command('create_google_calendar.py')):
        cmd = "cd " + settings.BASE_DIR + " && "
        cmd += settings.PYTHON + ' ' + os.path.join(settings.BASE_DIR, 'app4_ehpad_base/batch/create_google_calendar.py')
        cmd += " > " + settings.BASE_DIR + "/log/create_google_calendar.log 2>&1&"
        job = cron.new(command=cmd)
        # run every hours
        job.every(60).minutes()
        cron.write()


def install_cleaning_unsent():
    cron = CronTab(user=True)
    if not any(cron.find_command('clean_unsent.py')):
        cmd = "cd " + settings.BASE_DIR + " && "
        cmd += settings.PYTHON + ' ' + os.path.join(settings.BASE_DIR, 'app5_ehpad_messaging/batch/clean_unsent.py')
        cmd += " > " + settings.BASE_DIR + "/log/clean_unsent.log 2>&1&"
        job = cron.new(command=cmd)
        job.hours.on(23)
        cron.write()


def install_get_emails():
    cron = CronTab(user=True)
    if not any(cron.find_command('get_email_received.py')):
        cmd = "cd " + settings.BASE_DIR + " && "
        cmd += settings.PYTHON + ' ' + os.path.join(settings.BASE_DIR, 'app5_ehpad_messaging/batch/get_email_received.py')
        cmd += " > " + settings.BASE_DIR + "/log/get_email_received.log 2>&1&"
        job = cron.new(command=cmd)
        job.hours.on(23)
        cron.write()


if __name__ == '__main__':
    install_pics_counter_cron()
    install_thumbnails_cron()
    install_api_netsoins_cron()
    #install_cleaning_unsent()
    #install_get_emails()
    app5cron.install_algo_affectation()
    #install_create_calendar()