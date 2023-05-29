from django.urls import path
from . import views, api_ws, api

urlpatterns = [
    path('<str:myvideo>/', views.index, name='app7_video index'),
    path('video/parsed/', api_ws.send_parse_videos, name='app7_video download'),
    path('video/<str:folder>/<str:password>/', api.invalid_video, name='invalid video'),
    path('photo/profile/', api_ws.receive_profile_pic, name='profile pic')
    ]
