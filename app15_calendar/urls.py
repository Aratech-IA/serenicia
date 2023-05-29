from django.urls import path
from . import views

urlpatterns = [
    path('update/<int:pl_event_id>/<str:start>/<str:end>/', views.update_event,
         name='update cal event'),
    path('modal/<int:pl_event_id>/<str:editable>/', views.get_event_details,
         name='get event details'),
    path('delete/<int:pl_event_id>/', views.delete_event, name='delete cal event'),
    path('day/<int:year>/<int:month>/<int:day>/', views.calendar_day_view, name="app15_calendar day view"),
]
