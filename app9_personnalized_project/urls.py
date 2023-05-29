from django.urls import path
from . import views, genosociogram

urlpatterns = [
    path('', views.index, name='app9_personnalized_project index'),
    path('project/<int:survey_id>/', views.survey_answering, name='support project answering'),
    path('appointments/family/', views.appointments, name='support project appointments'),
    path('appointments/', views.employee_appointments, name='support project appointments employee'),
    path('storylife/<int:res_id>/', views.story_life, name='story life'),
    path('genosociogram/<int:family>/', genosociogram.genosociogram, name='genosociogram'),
    path('genosociogram/<int:family>/person/<int:person_id>/', genosociogram.person_details, name='person details'),
    path('genosociogram/<int:family>/person/create/<int:from_person>/<str:relation>/', genosociogram.create_person, name='create person'),
    path('genosociogram/download/full/<int:family>/', genosociogram.download_family, name='download family'),
    path('project/old/<int:import_id>', views.imported_project_pdf, name='old project pdf'),
    ]
