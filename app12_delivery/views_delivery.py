from django.contrib.auth.decorators import permission_required
from django.contrib.auth.models import Group
from django.core.exceptions import ObjectDoesNotExist
from django.http.response import HttpResponseRedirect
from django.shortcuts import render

# Create your views here.
from django.urls import reverse

from app1_base.models import Profile
from app12_delivery.form_registration import UserRegisterDeliveryForm, ProfileRegisterDeliveryForm, ContractRegisterForm, \
    ContractUpdateForm, CancelDeliveryForm, UserUpdateDeliveryForm, WeekOfContractForm, WeekOfContractUpdateForm, \
    MealsNumberForm
from app12_delivery.models import ContractDelivery, CancelDelivery, Delivery, InfoCustomerInvoice, DeliveryDay, WeekOfContract, \
    MealsNumber
from app12_delivery.util import getLatLon

# create relation and add field localisation profile or client
from app4_ehpad_base.models import ProfileSerenicia


@permission_required('app0_access.view_delivery')
def registercustomer(request):
    context = {}
    if request.method == 'POST':
        formUserDelivery = UserRegisterDeliveryForm(request.POST)
        formProfileDelivery = ProfileRegisterDeliveryForm(request.POST)
        if formUserDelivery.is_valid() & formProfileDelivery.is_valid():
            user, is_created = formUserDelivery.save()
            group = Group.objects.get(name="Customer Delivery")
            profile = formProfileDelivery.save(commit=False)
            if user and is_created:
                try:
                    lon, lat = getLatLon(formProfileDelivery.cleaned_data['adress'],
                                         formProfileDelivery.cleaned_data['city'],
                                         formProfileDelivery.cleaned_data['cp'])
                    profile.adress_latitude = lat
                    profile.adress_longitude = lon
                    profile.user = user
                    profile.save()
                    user.groups.add(group)
                    user.save()
                    context['created_user'] = user
                    context['username'] = user.username
                    context['pkProfile'] = profile.pk
                except:
                    user.delete()
                    context['error_adress'] = True
            else:
                context['error'] = True
    else:
        formUserDelivery = UserRegisterDeliveryForm()
        formProfileDelivery = ProfileRegisterDeliveryForm()
    context['UserRegisterDeliveryForm'] = formUserDelivery
    context['ProfileRegisterDeliveryForm'] = formProfileDelivery

    return render(request, 'app12_delivery/create_account_delivery.html', context)


@permission_required('app0_access.view_delivery')
def accountdeliveryupdate(request, pkCustomer):
    context = {}
    profile = Profile.objects.get(pk=pkCustomer)
    user = profile.user
    if request.method == 'POST':
        formUserDelivery = UserUpdateDeliveryForm(request.POST, instance=user)
        formProfileDelivery = ProfileRegisterDeliveryForm(request.POST, instance=profile)
        if formUserDelivery.is_valid() & formProfileDelivery.is_valid():
            try:
                formUserDelivery.save()
                profile_commit = formProfileDelivery.save(commit=False)
                lon, lat = getLatLon(formProfileDelivery.cleaned_data['adress'],
                                     formProfileDelivery.cleaned_data['city'], formProfileDelivery.cleaned_data['cp'])
                print(lon, lat)
                profile_commit.adress_latitude = lat
                profile_commit.adress_longitude = lon
                formProfileDelivery.save()
            except:
                context['error_adress'] = True
    else:
        formUserDelivery = UserUpdateDeliveryForm(instance=profile.user)
        formProfileDelivery = ProfileRegisterDeliveryForm(instance=profile)
    context['profile'] = profile
    context['UserUpdateDeliveryForm'] = formUserDelivery
    context['ProfileRegisterDeliveryForm'] = formProfileDelivery

    return render(request, 'app12_delivery/update_account_delivery.html', context)


@permission_required('app0_access.view_delivery')
def registercontract(request, pkCustomer):
    context = {"pkCustomer": pkCustomer}
    if request.method == 'POST':
        contractForm = ContractRegisterForm(request.POST)

        meals_numberForm = MealsNumberForm(request.POST)
        if contractForm.is_valid() and meals_numberForm.is_valid():
            contract = contractForm.save(commit=False)
            verify_contract = ContractDelivery.objects.filter(profile__pk=pkCustomer,
                                                              date_start_contract__range=[contract.date_start_contract,
                                                                                          contract.date_end_contract],
                                                              date_end_contract__range=[contract.date_start_contract,
                                                                                        contract.date_end_contract])
            if len(verify_contract) != 0:
                context['error'] = True
            else:
                profile_link = Profile.objects.get(pk=pkCustomer)
                contract.profile = profile_link
                contract.save()
                contractForm.save_m2m()
                day_contract = WeekOfContract.objects.create(contract_delivery=contract, )
                for idx, x in request.POST.lists():
                    if idx == "day_possibility":
                        for y in x:
                            if y == "monday":
                                day_contract.monday = True
                            if y == "tuesday":
                                day_contract.tuesday = True
                            if y == "wednesday":
                                day_contract.wednesday = True
                            if y == "thursday":
                                day_contract.thursday = True
                            if y == "friday":
                                day_contract.friday = True
                            if y == "saturday":
                                day_contract.saturday = True
                            if y == "sunday":
                                day_contract.sunday = True
                day_contract.save()
                meals_number = meals_numberForm.save(commit=False)
                meals_number.week_of_contract = day_contract
                meals_number.save()

                if contract:
                    context['created_contract'] = contract
                else:
                    context['error'] = True

    else:
        contractForm = ContractRegisterForm()
    week_of_contractForm = WeekOfContractForm()
    meals_numberForm = MealsNumberForm()

    context['formContractRegister'] = contractForm
    context['week_of_contractForm'] = week_of_contractForm
    context['meals_numberForm'] = meals_numberForm
    return render(request, 'app12_delivery/create_contract_delivery.html', context)


@permission_required('app0_access.view_delivery')
def listingaccountdelivery(request):
    context = {}
    # faire queryset avec filtre sur les permissions
    user_for_delivery = Profile.objects.filter(user__groups__name="Customer Delivery")
    context['user_for_delivery'] = user_for_delivery
    return render(request, 'app12_delivery/listing_account_delivery.html', context)


@permission_required('app0_access.view_delivery')
def accountdelivery(request, pkCustomer):
    context = {}
    profile = Profile.objects.get(pk=pkCustomer)
    contractProfile = ContractDelivery.objects.filter(profile__pk=profile.pk)
    cancel = CancelDelivery.objects.filter(profile__pk=pkCustomer)
    delivery = Delivery.objects.filter(profile=profile)
    try:
        if profile.infocustomerinvoice:
            info_user = InfoCustomerInvoice.objects.get(profile=profile)
            context["info_user"] = info_user
    except ObjectDoesNotExist:
        pass
    context["canceldelivery"] = cancel
    context["delivery"] = delivery
    context["customer"] = profile
    context["contractProfile"] = contractProfile
    return render(request, 'app12_delivery/account_delivery.html', context)


@permission_required('app0_access.view_delivery')
def contract_delivery(request, pkContract):
    context = {'pkContract': pkContract}
    contract = ContractDelivery.objects.get(pk=pkContract)
    day_contract = WeekOfContract.objects.get(contract_delivery=contract)
    number_meal = MealsNumber.objects.get(week_of_contract=day_contract.pk)
    if request.method == 'POST':
        contractForm = ContractUpdateForm(request.POST, instance=contract)
        week_of_contractForm = WeekOfContractUpdateForm(request.POST, instance=day_contract)
        meals_numberForm = MealsNumberForm(request.POST, instance=number_meal)
        if contractForm.is_valid() and week_of_contractForm.is_valid() and meals_numberForm.is_valid():
            contractForm.save()
            week_of_contractForm.save()
            meals_numberForm.save()
            context['contractForm'] = contractForm
            context['week_of_contractForm'] = week_of_contractForm

    else:
        contractForm = ContractUpdateForm(instance=contract)
        context['contractForm'] = contractForm
        week_of_contractForm = WeekOfContractUpdateForm(instance=day_contract)
        context['week_of_contractForm'] = week_of_contractForm
        meals_numberForm = MealsNumberForm(instance=number_meal)

    context['contract'] = contract
    context['day_contract'] = day_contract
    context['meals_numberForm'] = meals_numberForm
    return render(request, 'app12_delivery/contract_delivery.html', context)


@permission_required('app0_access.view_delivery')
def contractdeliverydelete(request, pkContract):
    contract = ContractDelivery.objects.get(pk=pkContract)
    redirect_profile = contract.profile.pk
    contract.delete()
    return HttpResponseRedirect(reverse("account_delivery", args=[redirect_profile]))


@permission_required('app0_access.view_delivery')
def canceldelivery(request, pkCustomer):
    context = {"pkCustomer": pkCustomer}
    profile = Profile.objects.get(pk=pkCustomer)
    if request.method == 'POST':
        cancelForm = CancelDeliveryForm(request.POST)
        if cancelForm.is_valid():
            cancel = cancelForm.save(commit=False)
            if len(CancelDelivery.objects.filter(date_cancel=cancel.date_cancel, profile=profile.pk)) == 0:
                cancel.profile = profile
                cancel.save()
                context['cancelForm'] = CancelDeliveryForm(cancelForm)
                return HttpResponseRedirect(reverse("account_delivery", args=[pkCustomer]))
            else:
                cancelForm = CancelDeliveryForm()
                context["error"] = True
    else:
        cancelForm = CancelDeliveryForm()
    context['cancelForm'] = cancelForm

    return render(request, 'app12_delivery/create_cancel_delivery.html', context)


@permission_required('app0_access.view_delivery')
def canceldeliverydelete(request, pkCancel):
    cancel = CancelDelivery.objects.get(pk=pkCancel)
    pkCustomer = cancel.profile.pk
    cancel.delete()
    return HttpResponseRedirect(reverse("account_delivery", args=[pkCustomer]))


@permission_required('app0_access.view_delivery')
def listing_cancel_delivery(request, pkCustomer):
    context = {}
    profile = Profile.objects.get(pk=pkCustomer)
    cancel = CancelDelivery.objects.filter(profile__pk=pkCustomer)
    context["customer"] = profile
    context["canceldelivery"] = cancel
    return render(request, 'app12_delivery/listing_cancel_delivery.html', context)
