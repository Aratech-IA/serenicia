from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='access index'),
    path('new/group/', views.new_group, name='new rights group'),
    path('group/', views.select_group, name='select rights group'),
    path('group/<int:grp_id>/', views.modify_group, name='modify rights group'),
    path('permissions/', views.select_group_by_permission, name='select group by permission'),
    path('user/<int:grp_id>/', views.select_user, name='select user'),
    path('user/modify/<int:user_id>/', views.modify_user, name='modify user'),
    path('user/types/', views.user_types, name='user types'),
]
