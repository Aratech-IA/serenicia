from django.urls import path

from app12_delivery import views_delivery, views_tour, views_main, views_invoice

# app_name = 'app12_delivery'


urlpatterns = [
    path('', views_main.home_delivery, name='home_delivery'),
    path('validateDelivery/<int:pkDelivery>', views_tour.validatedelivery, name='validate_delivery'),
    # tour
    path('tourmap/', views_tour.tourmap, name='tourmap'),
    path('tour_map_create/', views_tour.generateTour, name='generate_tour'),
    path('tour_map_delete/<int:pkTour>', views_tour.delete_tour, name='delete_tour'),
    path('tour_map_archive/<int:pkTourDelivery>', views_tour.tourmaparchive, name='tour_map_archive'),
    path('listing_tours/', views_tour.listingtours, name='listing_tours'),
    path('detailtour/<int:pkTourDelivery>', views_tour.detailtour, name='detail_tour'),
    path('detailtourtoday/', views_tour.detailtourtoday, name='detail_tour_today'),
    # path('exit_website/<path:str>', views_tour.exit_website, name='exit_website'),
    # list account delivery
    path('list_account_delivery/', views_delivery.listingaccountdelivery, name='list_account_delivery'),
    # cancel delivery
    path('register_cancel_delivery/<int:pkCustomer>', views_delivery.canceldelivery, name='cancel_delivery'),
    path('cancel_delivery/delete/<int:pkCancel>', views_delivery.canceldeliverydelete, name='cancel_delivery_delete'),
    path('listing_cancel_delivery/<int:pkCustomer>', views_delivery.listing_cancel_delivery, name='listing_cancel_delivery'),
    # register and manage a customer
    path('register_customer_delivery/', views_delivery.registercustomer, name='register_customer_delivery'),
    path('detail/<int:pkCustomer>', views_delivery.accountdelivery, name='account_delivery'),
    path('detail/update/<int:pkCustomer>', views_delivery.accountdeliveryupdate, name='account_delivery_update'),
    path('detail/register_contract_delivery/<int:pkCustomer>', views_delivery.registercontract, name='register_contract_delivery'),
    path('detail/contract_delivery/<int:pkContract>', views_delivery.contract_delivery, name='contract_delivery'),
    path('detail/contract_delivery/delete/<int:pkContract>', views_delivery.contractdeliverydelete, name='contract_delivery_delete'),
    # invoices
    path('benefits/', views_invoice.listing_benefit, name='listing_benefit'),
    path('invoices/', views_invoice.listing_invoice, name='listing_invoice'),
    path('invoice/<int:pkInvoiceHomePlus>', views_invoice.detail_invoice, name='detail_invoice'),
    # path('invoice_create/', views_invoice.invoice_create, name='invoice_create'),
    # path('add_benefice_to_invoice/', views_invoice.add_benefice_to_invoice, name='add_benefice_to_invoice')
    path('create_build_invoice/<int:pkInvoice>', views_invoice.create_build_invoice, name='create_build_invoice'),
    path('create_invoice/', views_invoice.create_invoice, name='create_invoice'),
    path('benefit_create/', views_invoice.benefit_create, name='benefit_create'),
    path('teletransmission/', views_invoice.teletransmission, name='teletransmission'),
    path('info_user_create/<int:pkCustomer>', views_invoice.info_user_create, name='info_user_create'),
    path('info_user_update/<int:pkCustomer>', views_invoice.info_user_update, name='info_user_update'),
    path('declaration_customer/', views_invoice.declaration_customer, name='declaration_customer'),
    path('search_declaration/', views_invoice.search_declaration, name='search_declaration'),


    # settings
    path('setting_day_done/', views_main.settingdaydone, name='setting_delivery_day_done'),
]
