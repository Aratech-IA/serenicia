from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='app8_survey index'),
    path('survey/<int:survey_id>/', views.survey_answering, name='survey answering'),
    path('survey/satisfaction/resident/', views.satisfaction_survey_resident, name='satisfaction survey resident'),
    path('survey/dashboard/', views.dashboard, name='app8_survey dashboard'),
    path('survey/dashboard/<int:survey_id>/', views.details, name='app8_survey dashboard details'),
    path('survey/dashboard/download/<int:survey_id>/', views.download_report, name='app8_survey download report'),
    ]
