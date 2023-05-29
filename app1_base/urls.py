from django.urls import path
from . import views

# from app1_base.admin import admin_protecia
#  app_name = 'app1_base'
urlpatterns = [
    path('', views.index, name='app1_base index'),
    path('camera/', views.camera, name='camera'),
    path('panel/detection/<int:first>/<int:alert>/<int:correction>/', views.panel, name='panel'),
    path('warning/<int:first_alert>/<str:key>', views.warning, name='warning'),
    path('warning_detail/<int:id>/<str:key>', views.warning_detail, name='warning_detail'),
    path('alert/', views.alert, name='alert'),
    path('alert/<str:suppr>/<str:pk>', views.alert, name='alert'),
    path('panel_detail/<int:id>', views.panel_detail, name='detail'),
    path('panel_detail/<int:id>/<int:box>', views.panel_detail, name='detail'),
    path('camera/last/<int:cam>', views.last, name='last image'),
    path('img/last/<int:cam_id>', views.get_last_analyse_img, name='image'),
    path('thumbnail/<int:im>/<str:key>/<int:w>/<int:h>', views.thumbnail, name='thumbnail'),
    path('get_video_token/<int:result>/<str:get_back>/<str:first>', views.get_video_token, name='video'),
    path('get_video_token/', views.get_video_token, name='video'),
    path('reboot/<int:profile>', views.reboot, name='reboot'),
    path('selection/', views.select_client, name='select location'),
    path('archive/', views.archive, name='archive'),
    path('autologin/', views.face_reco_login, name='face reco login'),
    path('timeline/', views.timeline, name='timeline'),
    path('preferences/', views.set_preferences, name='preferences')
]
