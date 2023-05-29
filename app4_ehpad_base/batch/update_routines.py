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
from django.contrib.auth.models import User

from app4_ehpad_base.models import ProfileSerenicia
# from app4_ehpad_base.views_calendar import google_update_clearance, updated_social_events
from app1_base.models import Client
from datetime import datetime, timedelta
import time, json, logging
from app1_base.log import Logger
from pprint import pprint


""" ALL FUNCTIONS CAN BE CALLED WITH NO PARAMETERS FOR ALL USERS 
OR WITH ONE APP1.MODELS.CLIENT FOR A SPECIFIC CLIENT
except get_upcomingdays() which is a subfunction"""


def update_google_routines(*args, **kwargs):
    # TODO setup a 70seconds CD every 500 requests
    if 'log_update_routines' not in globals():
        global log_update_routines
        log_update_routines = Logger('update_routines', level=logging.ERROR).run()

    log_update_routines.debug(f"entre dans update_google_routines:")

    try:
        with open("app4_ehpad_base/google_jsons/routines_loaded.json", "r") as jsonFile:
            json_copy = json.load(jsonFile)
    except OSError:
        with open("app4_ehpad_base/google_jsons/routines_loaded.json", "w") as jsonFile:
            data = {'init': []}
            json.dump(data, jsonFile)
    log_update_routines.debug(f"chargé le json des 'deja faits'")

    if args:
        residents_list = User.objects.get(pk=args[0].id)
    else:
        residents_list = User.objects.filter(groups__permissions__codename="view_residentehpad")

    # if args:
    #     residents_list = ProfileSerenicia.objects.get(pk=args[0].id)
    # else:
    #     residents_list = ProfileSerenicia.objects.filter(user__groups__permissions__codename="view_resident")
    for resident in residents_list:
        log_update_routines.debug(f"boucle client = {resident}")
        cal_id = resident.profileserenicia.cal_id
        upcomingdays = get_upcomingdays(resident.profileserenicia)
        try:
            done_list = json_copy[resident.profileserenicia.folder]
        except Exception:
            done_list = []
        day = 0
        for routine in upcomingdays:
            for r in routine[2]:
                dt = datetime.strptime(r['start'], "%H:%M")
                start = datetime.now().replace(hour=dt.hour, minute=dt.minute, second=0, microsecond=0) + timedelta(
                    days=day)
                if (asciified(r['type']+r['day_routine_id']+start.strftime('%Y%m%d%H%M%S'))) not in done_list:
                    id = asciified(r['type'] + r['day_routine_id'] + str(start))
                    rtn = setup_routine(resident.profileserenicia, id, start, r['duration'], r['type'], "")
                    try:
                        service().events().insert(calendarId=cal_id, body=rtn).execute()
                    except Exception as e:
                        print("error = {} \n".format(e))
                        log_update_routines.debug(f"pb update sur routine : {rtn}")
                        continue
            day += 1
        list_of_events = get_nine_days_list_of_events(cal_id)
        for day in list_of_events:
            i = 0
            for e in day:
                if e['id'] not in done_list:
                    done_list.append(e['id'])
            i += 1
        json_copy[resident.profileserenicia.folder] = done_list
        with open("app4_ehpad_base/google_jsons/routines_loaded.json", "w") as jsonFile:
            jsonFile.seek(0)
            json.dump(json_copy, jsonFile)
        log_update_routines.debug(f"enregistrement des routines faites pour {resident}")


def erase_google_routines(*args, **kwargs):
    """WORKS WITH ROUTINES_LOADED.JSON NOT TO DELETE ANY SOCIAL BY ACCIDENT
    ROUTINES SHOULD ONLY BE ADDED TO GOOGLE CALENDAR THROUGH UPDATE_GOOGLE_ROUTINES()"""
    # TODO reactivate "deleted events" if attempting to insert an already used ID cause they are google unique
    if args:
        residents_list = User.objects.get(pk=args[0].id)
    else:
        residents_list = User.objects.filter(groups__permissions__codename="view_residentehpad")
    try:
        with open("app4_ehpad_base/google_jsons/routines_loaded.json", "r") as jsonFile:
            json_copy = json.load(jsonFile)
    except OSError:
        with open("app4_ehpad_base/google_jsons/routines_loaded.json", "w") as jsonFile:
            data = {'init': []}
            json.dump(data, jsonFile)
    for resident in residents_list:
        cal_id = resident.profileserenicia.cal_id
        try:
            done_list = json_copy[resident.profileserenicia.folder]
        except Exception as e:
            print("error : {}".format(e))
            continue
        if done_list:
            for id in done_list:
                try:
                    service().events().list(calendarId=cal_id, eventId=id).execute()
                except Exception as e:
                    print("error : {}".format(e))


def update_google_socials(*args, **kwargs):
    if args:
        residents_list = User.objects.get(pk=args[0].id)
    else:
        residents_list = User.objects.filter(groups__permissions__codename="view_residentehpad")
    for resident in residents_list:
        cal_id = resident.profileserenicia.cal_id
        if google_update_clearance(resident.profileserenicia, cal_id):
            social_events = updated_social_events(resident.profileserenicia)
            day = 0
            for e in social_events[day][1:]:
                if e:
                    start = datetime.now().replace(hour=e[0][0]['event_date'].hour, minute=e[0][0]['event_date'].minute, second=0, microsecond=0) + timedelta(days=day)
                    evnt = setup_social_event(resident.profileserenicia, e[0][0]['user'], e[0][0]['event_id'], start, e[0][0]['event_duration_in_minutes'], e[0][0]['event_type'], e[0][0]['event_comment'])
                    try:
                        add_event(cal_id, evnt)
                    except Exception:
                        try:
                            update_event(cal_id, evnt['id'], evnt)
                        except Exception as e:
                            print("error : {}".format(e))
                day += 1


def apply_default_routines(*args, **kwargs):
    if args:
        residents_list = User.objects.get(pk=args[0].id)
    else:
        residents_list = User.objects.filter(groups__permissions__codename="view_residentehpad")
    profiles = RoutineProfile.objects.all()
    pprint(residents_list)
    pprint(profiles)
    for resident in residents_list:
        print("resident : {},\nprotocole routines : {}".format(resident, resident.profileserenicia.routines_protocol))
        if resident.profileserenicia.routines_protocol not in profiles:
            resident.profileserenicia.routines_protocol = RoutineProfile.objects.get_or_create(service_type="service standard")[0]
            print("routine inexistante, ajout : {}".format(RoutineProfile.objects.get_or_create(service_type="service standard")[0]))
            resident.save()
        for day in range(7):
            print("day : {}".format(day))
            try:
                rtn = DayRoutine.objects.filter(user_resident=resident).filter(jour=day).get()
                print("routine = {}".format(rtn))
                rtn.details = resident.profileserenicia.routines_protocol
                print("routine.details = {}".format(rtn.details))
                rtn.save()
            except Exception:
                print("routine du jour inexistante, création par defaut pour {}, jour: {}".format(resident, day))
                rtn = DayRoutine.objects.create(user_resident=resident, jour=day)
                rtn.details = resident.profileserenicia.routines_protocol
                rtn.save()


def get_upcomingdays(resident):
    upcomingdays = []
    tdelta = 9
    today = datetime.now()
    for i in range(tdelta):
        day = today + timedelta(days=i)
        try:
            routines = (DayRoutine.objects.filter(user_resident__profileserenicia=resident).filter(jour=day.weekday()).get()).details
            infos = routines.get_types_n_durations()
            routines = routines.get_list()
            calendar_date = [day.strftime("%a"), day.strftime("%d"), day.strftime("%b")]
            upcomingdays.append((calendar_date, routines, infos))
        except Exception as e:
            print("error : {}".format(e))
    return upcomingdays


if __name__ == '__main__':
    update_google_routines()
