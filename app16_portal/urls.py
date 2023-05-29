from django.urls import path

from . import views, views_site

urlpatterns = [
    path('', views.login_page, name='portal login'),
    path('selection/', views.index, name='portal index'),
    path('logout/', views.logout_page, name='portal logout'),
    path('site/infos/', views_site.site_infos, name='get site infos'),
    path('connexion/', views_site.login_from_portal, name='login from portal'),
    path('site/infos/key/', views_site.public_key, name='get public key'),
    path('user/add/', views_site.add_portal_user, name='add portal user'),
    path('user/update/', views_site.update_portal_user, name='update portal user'),
    path('add/key/', views_site.add_portal_key, name='add portal key'),
]
