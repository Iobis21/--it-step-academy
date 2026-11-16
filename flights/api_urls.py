from django.urls import path

from . import api

urlpatterns = [
    path('', api.index, name='api_index'),
    path('cities/', api.cities, name='api_cities'),
    path('airlines/', api.airlines, name='api_airlines'),
    path('flights/', api.flights, name='api_flights'),
    path('flights/<int:pk>/', api.flight_detail, name='api_flight_detail'),
    path('tickets/<str:pnr>/', api.ticket, name='api_ticket'),
]
