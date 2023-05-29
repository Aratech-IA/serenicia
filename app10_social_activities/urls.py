from django.urls import path

from . import views

urlpatterns = [
    path('', views.selection_activity, name='app10_social_activities index'),
    path('selected/', views.activity_index, name='app10_social_activities activity index'),
    path('selected/gallery/<int:act_id>/', views.gallery, name='app10_social_activities activity gallery'),
    path('selected/gallery/<int:act_id>/details/', views.gallery_details, name='app10_social_activities activity gallery details'),
    path('attendance/', views.attendance, name='app10_social_activities attendance'),
    path('dashboard/', views.dashboard, name='app10_social_activities dashboard'),
    path('selection/resident/', views.add_resident, name='app10_social_activities select resident'),
    path('identification/', views.auto_identification, name='app10_social_activities auto identification'),
    path('evaluate/', views.start_evaluation, name='app10_social_activities start evaluation'),
    path('evaluate/<int:question>', views.evaluate, name='app10_social_activities evaluate'),
    path('selection/voter/', views.select_voter, name='app10_social_activities select voter'),
    path('historic/', views.historic, name='app10_social_activities historic'),
    path('historic/<int:act_id>/', views.historic_details, name='app10_social_activities historic details'),
    path('historic/<int:act_id>/gallery/', views.gallery, name='app10_social_activities historic gallery'),
    path('historic/<int:act_id>/gallery/details/', views.gallery_details, name='app10_social_activities historic gallery details'),
    path('planning/', views.planning, name='app10_social_activities planning'),
]

