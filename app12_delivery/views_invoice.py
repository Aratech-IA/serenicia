import datetime
from uuid import uuid4

from django.contrib import messages
from django.contrib.auth.decorators import permission_required
from django.db import IntegrityError
from django.forms import modelformset_factory, formset_factory
from django.shortcuts import render, redirect

from app1_base.models import Profile
from app12_delivery.form_invoice import CreateBenefitForm, FeedInfoUserForm, InvoiceHomePlusForm, \
    DesignationInvoiceFormset
from app12_delivery.models import InvoiceHomePlus, DesignationInvoice, InfoCustomerInvoice, NumberDesignationPerInvoice


@permission_required('app0_access.view_delivery')
def listing_invoice(request):
    context = {}
    list_invoice = InvoiceHomePlus.objects.all()
    if len(list_invoice) == 0:
        context['empty'] = True
    else:
        context['list_invoice'] = list_invoice
    return render(request, 'app12_delivery/listing_invoice.html', context)


def detail_invoice(request):
    return None


# send data to URSSAF
def teletransmission(request):
    context = {}
    return render(request, 'app12_delivery/listing_invoice.html', context)


def search_declaration(request):
    return None


@permission_required('app0_access.view_delivery')
def create_invoice(request):
    now = datetime.datetime.now()
    number = 'INV-' + now.strftime("%Y-%m-") + str(uuid4()).split('-')[1]
    newInvoice = InvoiceHomePlus.objects.create(number=number, amount_without_vat=0)
    newInvoice.save()

    inv = InvoiceHomePlus.objects.get(number=number)
    return redirect('create_build_invoice', pkInvoice=inv.pk)


@permission_required('app0_access.view_delivery')
def create_build_invoice(request, pkInvoice):
    context = {}
    context['pkInvoice'] = pkInvoice
    # fetch that invoice

    try:
        invoice = InvoiceHomePlus.objects.get(pk=pkInvoice)
        list_provide = NumberDesignationPerInvoice.objects.filter(invoice_home_plus__pk=pkInvoice).values_list(
            'number_benefit', 'designation_invoice__price')
        price = int()
        for x in list_provide:
            price += x[0] * x[1]
        pass
    except:
        messages.error(request, 'Something went wrong')
        return redirect('home_delivery')
    context['price'] = price

    if request.method == 'GET':
        prod_form = DesignationInvoiceFormset()
        inv_form = InvoiceHomePlusForm(instance=invoice)
        context['prod_form'] = prod_form
        context['inv_form'] = inv_form
        return render(request, 'app12_delivery/create_invoice.html', context)

    if request.method == 'POST':
        inv_form = InvoiceHomePlusForm(request.POST, instance=invoice)
        prod_form = DesignationInvoiceFormset(request.POST)
        if inv_form.is_valid():
            inv_form.save(commit=False)
            print("here")
            inv_form.amount_without_vat = price
            inv_form.save()
            if prod_form.has_changed() and prod_form.is_valid():
                for form in prod_form:
                    if form.has_changed():
                        form_to_save = form.save(commit=False)
                        form_to_save.invoice_home_plus = invoice
                        form_to_save.save()
                messages.success(request, "Invoice product added succesfully")
                return redirect('create_build_invoice', pkInvoice=pkInvoice)
            messages.success(request, "Invoice updated succesfully")
            return redirect('create_build_invoice', pkInvoice=pkInvoice)
        else:
            context['prod_form'] = prod_form
            context['inv_form'] = inv_form
            print("la")
            messages.error(request, "Problem processing your request")
            return render(request, 'app12_delivery/create_invoice.html', context)

    return render(request, 'app12_delivery/create_invoice.html', context)


@permission_required('app0_access.view_delivery')
def benefit_create(request):
    context = {}
    if request.method == 'POST':
        formBenefit = CreateBenefitForm(request.POST)
        if formBenefit.is_valid():
            formBenefit.save()
            context['is_created'] = True
    else:
        formBenefit = CreateBenefitForm()
    context['formBenefit'] = formBenefit
    return render(request, 'app12_delivery/benefit_create.html', context)


@permission_required('app0_access.view_delivery')
def listing_benefit(request):
    context = {}
    list_benefit = DesignationInvoice.objects.all()
    if len(list_benefit) == 0:
        context['is_empty'] = True
    else:
        context['list_benefit'] = list_benefit
    return render(request, 'app12_delivery/listing_benefit.html', context)


@permission_required('app0_access.view_delivery')
def info_user_create(request, pkCustomer):
    context = {}
    if request.method == 'POST':
        formFeedInfoUser = FeedInfoUserForm(request.POST)
        if formFeedInfoUser.is_valid():
            try:
                commitProfile = formFeedInfoUser.save(commit=False)
                profile = Profile.objects.get(pk=pkCustomer)
                commitProfile.profile = profile
                commitProfile.save()
                context['is_created'] = True
            except IntegrityError:
                context['if_exist'] = True

    else:
        formFeedInfoUser = FeedInfoUserForm()
    context['formFeedInfoUser'] = formFeedInfoUser
    context['pkCustomer'] = pkCustomer
    return render(request, 'app12_delivery/info_user.html', context)


@permission_required('app0_access.view_delivery')
def info_user_update(request, pkCustomer):
    context = {}
    info_user = InfoCustomerInvoice.objects.get(profile__pk=pkCustomer)
    if request.method == 'POST':
        formFeedInfoUser = FeedInfoUserForm(request.POST, instance=info_user)
        if formFeedInfoUser.is_valid():
            commitProfile = formFeedInfoUser.save(commit=False)
            profile = Profile.objects.get(pk=pkCustomer)
            commitProfile.profile = profile
            commitProfile.save()
    else:
        formFeedInfoUser = FeedInfoUserForm(instance=info_user)
    context['formFeedInfoUser'] = formFeedInfoUser
    context['pkCustomer'] = pkCustomer
    return render(request, 'app12_delivery/info_user.html', context)


# need to create a view for listing customer haven't sent declaration
def declaration_customer(request):
    return None
