from django.urls import path
from django.utils.translation import gettext_lazy as _
from . import views


urlpatterns = [
    path('', views.index, name='app17_help index'),
    path('social_life', views.social_life, name='app17_help social_life'),
    path('cuisine', views.cuisine, name='app17_help cuisine'),
]