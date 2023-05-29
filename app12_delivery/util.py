import requests
from geopy import Nominatim


#
# def belongToGroup(requests):
#     usr_grp = requests.user.groups.filter(name="Delivery Business" or "Delivery Man" or "Customer Delivery")
#     if  usr_grp:
#
#     else:
#     perm = list(map(lambda x: x.name if x == "Delivery Business" or "Delivery Man" or "Customer Delivery" else False,
#                     requests.user.groups.all()))
#     return usr_grp
#     # return str(requests.user.groups.all()[0].name)


# def getLatLon(adress, city, cp):
#
#     full_adress = adress + "," + city + "," + cp
#     sender_request = requests.get(full_adress)
#     jsonMapBox = sender_request.json()
#     jsonMapBox.
#     adress_longitude = coordinates.longitude
#     adress_latitude = coordinates.latitude
#     return adress_longitude, adress_latitude


def getLatLon(adress, city, cp):
    full_adress = adress + "," + city + "," + cp
    geolocator = Nominatim(user_agent="deliveryMeal")
    coordinates = geolocator.geocode(full_adress)
    adress_longitude = coordinates.longitude
    adress_latitude = coordinates.latitude
    return adress_longitude, adress_latitude
