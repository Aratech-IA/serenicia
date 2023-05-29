import json
from datetime import timedelta, date

from django.contrib.auth.decorators import permission_required
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.db.utils import IntegrityError
from django.http.response import HttpResponseRedirect
from django.shortcuts import render, redirect
from django.urls import reverse

from app12_delivery.models import TourDelivery, Delivery
from projet.settings.settings import KEY_API_MAPBOX


@permission_required('app0_access.view_delivery')
def detailtour(request, pkTourDelivery):
    context = {}
    tour = TourDelivery.objects.get(pk=pkTourDelivery)
    tourDetail = Delivery.objects.filter(tour_delivery=tour).order_by('order')
    context['tour'] = tour
    context['tourDetail'] = tourDetail
    return render(request, 'app12_delivery/detail_tour.html', context)


@permission_required('app0_access.view_delivery')
def detailtourtoday(request):
    context = {}
    try:
        tour = TourDelivery.objects.get(date_tour_delivery=date.today())
        tourDetail = Delivery.objects.filter(tour_delivery=tour).order_by('order')
        context['tour'] = tour
        context['tourDetail'] = tourDetail
    except:
        context['tourDontExist'] = True
        return HttpResponseRedirect(reverse("home_delivery"))
    return render(request, 'app12_delivery/detail_tour_today.html', context)


@permission_required('app0_access.view_delivery')
def tourmap(request):
    context = {}
    try:
        # seeding component validate
        today = date.today()
        delivery = Delivery.objects.filter(tour_delivery__date_tour_delivery=today).order_by('order')
        context['delivery'] = delivery
        # get start point
        entreprise = User.objects.filter(groups__name="Delivery Business").first()
        entreprise_latitude = entreprise.profile.adress_latitude
        entreprise_longitude = entreprise.profile.adress_longitude
        tourdelivery = TourDelivery.objects.get(date_tour_delivery=today)
        context["tourdelivery"] = json.dumps(tourdelivery.tour_delivery_routing)
        context["entreprise_latitude"] = entreprise_latitude
        context["entreprise_longitude"] = entreprise_longitude
        context["KEY_API_MAPBOX"] = KEY_API_MAPBOX
    except ObjectDoesNotExist:
        context["have_not_delivery"] = "Vous n'avez pas de tournée prevu aujourd'hui"
    return render(request, 'app12_delivery/tourMap.html', context)


@permission_required('app0_access.view_delivery')
def validatedelivery(request, pkDelivery):
    deliveryValidate = Delivery.objects.get(pk=pkDelivery)
    updateJsonOld = deliveryValidate.tour_delivery.tour_delivery_routing
    dataToUpdate = TourDelivery.objects.get(pk=deliveryValidate.tour_delivery.pk)
    if deliveryValidate.finish:
        deliveryValidate.finish = False
        for x in updateJsonOld['waypoints']:
            if deliveryValidate.profile.pk == x['userInfo']['pk']:
                x['userInfo']['is_finish'] = False
                pass
    else:
        deliveryValidate.finish = True
        for x in updateJsonOld['waypoints']:
            if deliveryValidate.profile.pk == x['userInfo']['pk']:
                x['userInfo']['is_finish'] = True
                pass
    dataToUpdate.tour_delivery_routing = updateJsonOld
    dataToUpdate.save()
    deliveryValidate.save()
    return HttpResponseRedirect(reverse("tourmap"))


@permission_required('app0_access.view_delivery')
def tourmaparchive(request, pkTourDelivery):
    context = {}
    try:
        entreprise = User.objects.filter(groups__name="Delivery Business").first()
        entreprise_latitude = entreprise.profile.adress_latitude
        entreprise_longitude = entreprise.profile.adress_longitude
        tourdelivery = TourDelivery.objects.get(pk=pkTourDelivery)
        context["tourdelivery"] = json.dumps(tourdelivery.tour_delivery_routing)
        context["entreprise_latitude"] = entreprise_latitude
        context["entreprise_longitude"] = entreprise_longitude
        context["KEY_API_MAPBOX"] = KEY_API_MAPBOX
    except ObjectDoesNotExist:
        context["have_not_delivery"] = "Erreur la donnée est corrompu"
    return render(request, 'app12_delivery/tourArchiveTour.html', context)


@permission_required('app0_access.view_delivery')
def listingtours(request, **is_sucess):
    context = {}
    tour_for_delivery = TourDelivery.objects.order_by('-date_tour_delivery').all()
    context['tour_for_delivery'] = tour_for_delivery
    return render(request, 'app12_delivery/listing_tours.html', context)


@permission_required('app0_access.view_delivery')
def generateTour(request):
    context = {}
    try:
        from app12_delivery.batch.auto_ordering_tour import ordering_tour
        ordering_tour()
        is_success = True
    except IntegrityError:
        is_success = False

    context['is_success'] = is_success
    return HttpResponseRedirect(reverse("listing_tours"), context)


@permission_required('app0_access.view_delivery')
def delete_tour(request, pkTour):
    tour_delete = TourDelivery.objects.get(pk=pkTour)
    tour_delete.delete()
    return redirect('home_delivery')
