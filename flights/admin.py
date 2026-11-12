from django.contrib import admin

from .models import Airline, Booking, City, Favorite, Flight, Passenger


@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = ['name', 'airport_code']
    search_fields = ['name', 'airport_code']


@admin.register(Airline)
class AirlineAdmin(admin.ModelAdmin):
    list_display = ['name', 'code']


@admin.register(Flight)
class FlightAdmin(admin.ModelAdmin):
    list_display = ['flight_number', 'airline', 'origin', 'destination', 'departure_time', 'economy_price', 'stops']
    list_filter = ['airline', 'origin', 'destination', 'stops']
    search_fields = ['flight_number']
    date_hierarchy = 'departure_time'


class PassengerInline(admin.TabularInline):
    model = Passenger
    extra = 0


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'flight', 'cabin', 'total_price', 'status', 'created_at']
    list_filter = ['status', 'cabin']
    inlines = [PassengerInline]


admin.site.register(Favorite)
