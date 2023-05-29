from django.urls import path

from . import views

urlpatterns = [
    path('', views.test, name='app13_resident index'),
    path('indexold/', views.index, name='app13_resident indexold'),
    path('albums/', views.list_albums_photo, name="app13_resident list album photo"),
    path('albums/<str:name>/', views.photo_from_album, name="app13_resident photo from album"),
    path('menus/', views.menus, name='app13_resident menus'),
    path('menus/entree/<str:evaltype>/', views.menus_entree, name='app13_resident evaluation entree'),
    path('menus/maindish/<str:evaltype>/', views.menus_main_dish, name='app13_resident eval main dish'),
    path('menus/dessert/<str:evaltype>/', views.menus_dessert, name='app13_resident eval dessert'),
    path('menus/finalize/<str:evaltype>/', views.menus_finalize, name='app13_resident eval finalize'),
    path('videochat/', views.get_contact_for_call, name='app13_resident contact for call'),
    path('videochat/call/', views.videochat, name='app13_resident videochat'),
    path('auth/<str:token>/', views.auth, name="index auth"),
    path('interventions/', views.interventions, name='interventions')
]
