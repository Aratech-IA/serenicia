from . import views

from django.urls import path

urlpatterns = [
    path('', views.profile, name='profile'),
    path('password/', views.change_password, name='change_password'),
]
