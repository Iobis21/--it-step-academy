from django.urls import path

from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('search/', views.search, name='search'),
    path('flights/<int:pk>/', views.flight_detail, name='flight_detail'),
    path('flights/<int:pk>/book/', views.book, name='book'),
    path('flights/<int:pk>/favorite/', views.toggle_favorite, name='toggle_favorite'),
    path('bookings/<int:pk>/cancel/', views.cancel_booking, name='cancel_booking'),
    path('profile/', views.profile, name='profile'),
]
