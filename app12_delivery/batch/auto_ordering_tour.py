import json
import os
import sys
from datetime import datetime
import datetime as timedeldate

from django.db.models import Q

from projet.settings.settings import KEY_API_MAPBOX

try:
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
except NameError:
    sys.path.append(os.path.abspath('../..'))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "projet.settings.settings")
import django

django.setup()

from django.contrib.auth.models import User
import requests
from django.db.utils import IntegrityError

from app1_base.models import Profile
from app12_delivery.models import TourDelivery, Delivery, DeliveryDay


# ft returne a list order to waypoint (limit to 12 waypoints at once)
# def optimized_tour(coordinates_waypoints: list):
def optimized_tour(coordinates_waypoints: list):
    # create url for API
    API_key = KEY_API_MAPBOX
    api_url = "https://api.mapbox.com/optimized-trips/v1/mapbox/driving-traffic/"
    end_api_url = "?access_token=" + API_key
    # retrieve coordinates in list
    coordinates = str()
    for x in coordinates_waypoints:
        coordinates += str(x[0] + "," + x[1] + ";")
    # remove ;
    coordinates = coordinates[:-1]
    # get json with coordinates
    sender_request = requests.get(api_url + coordinates + end_api_url)
    json_optimized = sender_request.json()
    # get order waypoints and fusion with param list
    for xid, x in enumerate(json_optimized['waypoints']):
        coordinates_waypoints[xid].append(x['waypoint_index'])

    # sort param list
    def takeThirdly(elem):
        return elem[2]

    coordinates_waypoints.sort(key=takeThirdly)
    return coordinates_waypoints


def ordering_tour(target_day=datetime.today().date()):
    # find all user will to delivery target_day
    all_customer = User.objects.filter((Q(profile__contractdelivery__date_end_contract__gte=target_day) | Q(
        profile__contractdelivery__date_end_contract__isnull=True)), groups__name="Customer Delivery",
                                       profile__contractdelivery__date_start_contract__lte=target_day,
                                       ).exclude(
        profile__canceldelivery__date_cancel=target_day)
    # get start point
    entreprise = User.objects.filter(groups__name="Delivery Business").first()
    entreprise_latitude = entreprise.profile.adress_latitude
    entreprise_longitude = entreprise.profile.adress_longitude
    coordinates = str()
    API_key = KEY_API_MAPBOX
    api_url = "https://api.mapbox.com/directions/v5/mapbox/driving-traffic/" + entreprise_longitude + "," + entreprise_latitude
    nb_waypoint = 0
    day_delivery = DeliveryDay.objects.first()
    all_customer = list(all_customer)
    customer_to_date = list()
    for idx, x in enumerate(all_customer):
        contract_active_for_day = x.profile.contractdelivery_set.get(
            (Q(profile__contractdelivery__date_end_contract__gte=target_day) |
             Q(profile__contractdelivery__date_end_contract__isnull=True)),
            date_start_contract__lte=target_day)
        if day_delivery.get_day_valid(contract_active_for_day.weekofcontract, target_day.strftime('%A')):
            # coordinates += ";" + x.profile.adress_longitude + "," + x.profile.adress_latitude
            # nb_waypoint += 1
            customer_to_date.append(x)
    # create a list coordinate
    list_to_optimized_tour = list()
    for x in customer_to_date:
        list_to_optimized_tour.append([x.profile.adress_longitude, x.profile.adress_latitude])
    coordinates_optimized = optimized_tour(list_to_optimized_tour)
    for x in coordinates_optimized:
        coordinates += ";"+x[0]+","+x[1]
    print(coordinates)
    end_api_url = ";" + entreprise_longitude + "," + entreprise_latitude + "?geometries=geojson&steps=false&alternatives=false&overview=full&access_token=" + API_key
    try:
        sender_request = requests.get(api_url + coordinates + end_api_url)
        print(api_url + coordinates + end_api_url)
        jsonMapBox = sender_request.json()
        t = datetime(year=1, month=1, day=1) + timedeldate.timedelta(
            minutes=int(jsonMapBox['routes'][0]['duration'] / 60))
        tour_register = TourDelivery.objects.create(date_tour_delivery=target_day, time_estimate=t,
                                                    tour_delivery_routing=jsonMapBox, profile=entreprise.profile)
        jsonInfoUser = list()
        for coordinatesUser in customer_to_date:
            aUserInfo = dict()
            aUserInfo['pk'] = coordinatesUser.profile.pk
            aUserInfo['last_name'] = coordinatesUser.profile.user.last_name
            aUserInfo['adress'] = coordinatesUser.profile.adress
            aUserInfo['city'] = coordinatesUser.profile.city
            aUserInfo['cp'] = coordinatesUser.profile.cp
            aUserInfo['adress_longitude'] = coordinatesUser.profile.adress_longitude
            aUserInfo['adress_latitude'] = coordinatesUser.profile.adress_latitude
            aUserInfo['is_finish'] = False
            jsonInfoUser.append(aUserInfo)
        jsonInfoUser.append({'pk': entreprise.profile.pk, 'last_name': entreprise.last_name,
                             'adress': entreprise.profile.adress, 'city': entreprise.profile.city,
                             'cp': entreprise.profile.cp,
                             'adress_longitude': entreprise.profile.adress_longitude,
                             'adress_latitude': entreprise.profile.adress_latitude,
                             'is_finish': False,
                             'business': True,
                             })
        jsonInfoUser.insert(0, {'pk': entreprise.profile.pk, 'last_name': entreprise.last_name,
                                'adress': entreprise.profile.adress, 'city': entreprise.profile.city,
                                'cp': entreprise.profile.cp,
                                'adress_longitude': entreprise.profile.adress_longitude,
                                'adress_latitude': entreprise.profile.adress_latitude,
                                'is_finish': False,
                                'business': True
                                })
        for idx, i in enumerate(jsonMapBox['waypoints']):
            pkProfile = int(jsonInfoUser[idx]['pk'])
            profileLink = Profile.objects.get(pk=pkProfile)
            Delivery.objects.create(order=idx, finish=False, tour_delivery=tour_register,
                                    profile=profileLink)
            jsonMapBox['waypoints'][idx]['userInfo'] = jsonInfoUser[idx]
        tour_register.tour_delivery_routing = jsonMapBox
        tour_register.save()
    except IntegrityError:
        print("la tournée existe déjà")
