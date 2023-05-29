from django.urls import path
from . import views, views_signup


urlpatterns = [
        path('messagerie/send/family', views.internal_emailing_family, name='internal_emailing_family'),
        path('notif/auto/doctor_date/<int:doctor>/<int:day>', views.add_date_doctor, name='add_date_doctor'),
        # path('register/', views_signup.register, name='register'),
        path('register/<str:mod>', views_signup.register_user, name="register_user"),
]
