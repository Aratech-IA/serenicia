from math import ceil

from django.contrib.auth.models import User
from django.db.models import Sum

from app6_care.models import SectorNappy


# ------------------------------------------related to SectorNappy model------------------------------------------------
def consumption_next_7_days_per_sector(sector_nappy):
    quantity = 1
    daily_consumption = 0
    for loop in range(10):
        users_for_current_quantity = len(User.objects.filter(profileserenicia__status='home',
                                                             profile__client__sector=sector_nappy.sector,
                                                             usernappy__nappy=sector_nappy.nappy,
                                                             usernappy__quantity=quantity))
        daily_consumption += users_for_current_quantity * quantity
        quantity += 1
    return daily_consumption * 7


def nappies_to_restock_per_sector(sector_nappy):
    actual_stock = SectorNappy.objects.get(sector=sector_nappy.sector, nappy=sector_nappy.nappy).stock
    difference = consumption_next_7_days_per_sector(sector_nappy) - actual_stock
    if difference <= 0:
        return 0
    else:
        return difference


# --------------------------------------------related to Nappy model----------------------------------------------------
def consumption_next_7_days(nappy):
    quantity = 1
    daily_consumption = 0
    for loop in range(10):
        users_for_current_quantity = len(User.objects.filter(profileserenicia__status='home',
                                                             usernappy__nappy=nappy,
                                                             usernappy__quantity=quantity))
        daily_consumption += users_for_current_quantity * quantity
        quantity += 1
    return daily_consumption * 7


def nappies_total_stock(nappy):
    nappies_stock_in_sectors = SectorNappy.objects.filter(nappy=nappy).aggregate(Sum('stock'))['stock__sum'] or 0
    nappies_stock_in_storehouse = nappy.stock_in_storehouse or 0
    return nappies_stock_in_sectors + nappies_stock_in_storehouse


def boxes_to_order_for_next_week(nappy):
    nappies_to_order = consumption_next_7_days(nappy) * nappy.order_security - nappies_total_stock(nappy)
    boxes_to_order = nappies_to_order / nappy.nappies_per_bag / nappy.bags_per_box
    if boxes_to_order <= 0:
        return 0
    else:
        return ceil(boxes_to_order)
