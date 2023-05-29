from django.urls import path

from . import views
from app2_machine_learning.admin import admin_site

urlpatterns = [
    path('', views.index, name='app2_machine_learning index'),
    path('admin/', admin_site.urls),
    path('dataset/<str:dataset>', views.dataset, name='dataset'),
    path('dataset/<str:dataset>/<str:img_name>',  views.img, name='image')
]