import datetime
from math import ceil

from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.forms import formset_factory
from django.utils import timezone


from app6_care.models import Nappy, SectorNappy, Treatment
from app6_care.forms.forms_nappy_management import OrderForm, DeliveryForm, SectorInventoryForm, StorehouseInventoryForm, \
    ReStockForm
from app6_care.nappy_stock import nappies_total_stock, boxes_to_order_for_next_week, nappies_to_restock_per_sector, \
    consumption_next_7_days, consumption_next_7_days_per_sector


@login_required
def views_nappy_management(request):
    request.session['resident_id'] = None

    return render(request, 'app6_care/nappy_management/nappy_management.html')


@login_required
def views_nappy_order(request):
    OrderFormset = formset_factory(OrderForm, extra=0)
    initial_data = [
        {'id': nappy.id,
         'name': nappy.name,
         'total_stock': round(nappies_total_stock(nappy) / nappy.nappies_per_bag / nappy.bags_per_box, 1),
         'consumption_past_7_days': len(Treatment.objects.filter(nappy=nappy,
                                                                 date__lte=timezone.now()-datetime.timedelta(days=7))),
         'consumption_next_7_days': round(consumption_next_7_days(nappy) / nappy.nappies_per_bag / nappy.bags_per_box,
                                          1),
         'order': boxes_to_order_for_next_week(nappy)}
        for nappy in Nappy.objects.all()
    ]

    if request.method == 'POST':
        formset = OrderFormset(request.POST, initial=initial_data)
        if formset.is_valid():
            for form in formset:
                if form.cleaned_data['order'] > 0:
                    nappy = Nappy.objects.get(pk=form.cleaned_data['id'])
                    order = form.cleaned_data['order']
                    # do something

        return HttpResponseRedirect('/app6_care/nappy_management/nappy_order/')

    else:
        formset = OrderFormset(initial=initial_data)

    return render(request, 'app6_care/nappy_management/nappy_order.html', {'formset': formset})


@login_required
def views_nappy_delivery(request):
    DeliveryFormset = formset_factory(DeliveryForm, extra=0)
    initial_data = [{'id': nappy.id, 'name': nappy.name, 'boxes': 0} for nappy in Nappy.objects.all()]

    if request.method == 'POST':
        formset = DeliveryFormset(request.POST, initial=initial_data)
        if formset.is_valid():
            for form in formset:
                if form.cleaned_data['boxes'] > 0:
                    nappy = Nappy.objects.get(pk=form.cleaned_data['id'])
                    nappy.stock_in_storehouse += form.cleaned_data['boxes'] * nappy.nappies_per_bag * nappy.bags_per_box
                    nappy.save()
        return HttpResponseRedirect('/app6_care/nappy_delivery/')

    else:
        formset = DeliveryFormset(initial=initial_data)

    return render(request, 'app6_care/nappy_management/nappy_delivery.html', {'formset': formset})


@login_required
def views_nappy_inventory(request):
    # a unique formset for the storehouse inventory
    StorehouseInventoryFormset = formset_factory(StorehouseInventoryForm, extra=0)
    storehouse_initial_data = [{'id': nappy.id, 'name': nappy.name, 'stock': nappy.stock_in_storehouse,
                                'real_stock': nappy.stock_in_storehouse} for nappy in Nappy.objects.all()]
    formsets = []
    formsets_initial_data = []
    SectorInventoryFormset = formset_factory(SectorInventoryForm, extra=0)
    sectors = [sector_nappy.sector for sector_nappy in SectorNappy.objects.order_by('sector_id').distinct('sector_id')]

    # data initialization (sectors inventory = 1 formset per sector)
    for sector in sectors:
        initial_data = [{'id': sector_nappy.id, 'name': sector_nappy.nappy.name, 'stock': sector_nappy.stock,
                         'real_stock': sector_nappy.stock} for sector_nappy in SectorNappy.objects.filter(sector=sector)
                        ]
        formsets_initial_data.append(initial_data)

    if request.method == 'POST':
        # POST storehouse inventory
        storehouse_formset = StorehouseInventoryFormset(request.POST, initial=storehouse_initial_data,
                                                        prefix='storehouse')
        if storehouse_formset.is_valid():
            for form in storehouse_formset:
                nappy = Nappy.objects.get(pk=form.cleaned_data['id'])
                nappy.stock_in_storehouse = form.cleaned_data['real_stock']
                nappy.save()

        # POST inventory per sector
        i = 0
        for initial_data in formsets_initial_data:
            formset = SectorInventoryFormset(request.POST, initial=initial_data, prefix=sectors[i])
            formsets.append(formset)
            i += 1
            if formset.is_valid():
                for form in formset:
                    sector_nappy = SectorNappy.objects.get(pk=form.cleaned_data['id'])
                    sector_nappy.stock = form.cleaned_data['real_stock']
                    sector_nappy.save()
        return HttpResponseRedirect('/app6_care/nappy_management/nappy_inventory/')

    else:
        storehouse_formset = StorehouseInventoryFormset(initial=storehouse_initial_data, prefix='storehouse')

        # GET inventory per sector
        i = 0
        for initial_data in formsets_initial_data:
            formset = SectorInventoryFormset(initial=initial_data, prefix=sectors[i])
            formsets.append(formset)
            i += 1

    return render(request, 'app6_care/nappy_management/nappy_inventory.html', {'storehouse_formset': storehouse_formset,
                                                                          'formsets': formsets, 'sectors': sectors})


@login_required
def views_nappy_restock(request):
    formsets_initial_data = []
    formsets = []
    ReStockFormset = formset_factory(ReStockForm, extra=0)
    total_to_restock = []
    sectors = [sector_nappy.sector for sector_nappy in SectorNappy.objects.order_by('sector_id').distinct('sector_id')]
    nappies = [sector_nappy.nappy for sector_nappy in SectorNappy.objects.order_by('nappy_id').distinct('nappy_id')]

    # data initialization (1 formset per sector)
    for sector in sectors:
        initial_data = [
            {'id': sector_nappy.id, 'name': sector_nappy.nappy.name, 'actual_stock': sector_nappy.stock,
             'consumption_next_7_days': consumption_next_7_days_per_sector(sector_nappy),
             'restock': nappies_to_restock_per_sector(sector_nappy)}
            for sector_nappy in SectorNappy.objects.filter(sector=sector)
        ]
        formsets_initial_data.append(initial_data)

    for nappy in nappies:
        to_restock = 0
        for sector_nappy in SectorNappy.objects.filter(nappy=nappy):
            to_restock += nappies_to_restock_per_sector(sector_nappy)
        total_to_restock.append({'name': nappy.name, 'bags_to_restock': ceil(to_restock/nappy.nappies_per_bag),
                                 'nappies_per_bag': nappy.nappies_per_bag})

    if request.method == 'POST':
        i = 0
        for initial_data in formsets_initial_data:
            formsets.append(ReStockFormset(request.POST, initial=initial_data, prefix=sectors[i]))
            i += 1
        for formset in formsets:
            if formset.is_valid():
                for form in formset:
                    sector_nappy = SectorNappy.objects.get(pk=form.cleaned_data['id'])
                    sector_nappy.stock += form.cleaned_data['restock']
                    sector_nappy.save()
        return HttpResponseRedirect('/app6_care/nappy_restock/')

    else:
        i = 0
        for initial_data in formsets_initial_data:
            formsets.append(ReStockFormset(initial=initial_data, prefix=sectors[i]))
            i += 1

    return render(request, 'app6_care/nappy_management/nappy_restock.html',
                  {'formsets': formsets, 'total_to_restock': total_to_restock})
