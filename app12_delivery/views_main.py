from django.contrib.auth.decorators import permission_required
from django.contrib.auth.models import Permission, User
from django.forms import modelformset_factory
from django.shortcuts import render

from app1_base.models import Profile
from app12_delivery.form_setting import DeliveryDayForm
from app12_delivery.models import TourDelivery, DeliveryDay


@permission_required('app0_access.view_delivery')
def home_delivery(request):
    context = {}
    # if Permission.objects.filter(user=request.user.id, codename='view_delivery'):
    user_connected = User.objects.get(pk=request.user.id)
    if user_connected.groups.filter(permissions__codename='view_delivery').exists():
        user_for_delivery = Profile.objects.filter(user__groups__name="Customer Delivery")[:15]
        context['user_for_delivery'] = user_for_delivery
        tour = TourDelivery.objects.order_by('-date_tour_delivery')[:15]
        context['tour'] = tour
    return render(request, 'app12_delivery/home.html', context)


@permission_required('app0_access.view_delivery')
def settingdaydone(request):
    context = {}
    week_day_active = DeliveryDay.objects.first()
    if request.method == 'POST':
        day_form = DeliveryDayForm(request.POST, instance=week_day_active)
        if day_form.is_valid():
            day_form.save()
        context['week_day_active_form'] = day_form
    else:
        week_day_active_form = DeliveryDayForm(instance=week_day_active)
        context['week_day_active_form'] = week_day_active_form

    return render(request, 'app12_delivery/setting_day_done.html', context)
