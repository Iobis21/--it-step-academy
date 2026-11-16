from django.contrib import admin
from django.db.models import Count

from .models import Airline, Booking, City, Favorite, Flight, Passenger

admin.site.site_header = 'SkyBook — ადმინ პანელი'
admin.site.site_title = 'SkyBook ადმინი'
admin.site.index_title = 'მართვა'


@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = ['name', 'airport_code']
    search_fields = ['name', 'airport_code']


@admin.register(Airline)
class AirlineAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'low_cost']
    list_filter = ['low_cost']


@admin.register(Flight)
class FlightAdmin(admin.ModelAdmin):
    list_display = ['flight_number', 'airline', 'origin', 'destination', 'departure_time',
                    'economy_price', 'business_price', 'stops', 'sold_seats']
    list_filter = ['airline', 'origin', 'destination', 'stops']
    search_fields = ['flight_number']
    date_hierarchy = 'departure_time'

    @admin.display(description='გაყიდული ადგილი')
    def sold_seats(self, obj):
        return f'{len(obj.taken_seats())} / {obj.seats_total}'


class PassengerInline(admin.TabularInline):
    model = Passenger
    extra = 0
    fields = ['flight', 'seat', 'first_name', 'last_name', 'passport', 'extra_cabin_bag', 'extra_checked_bags', 'checked_in']


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ['pnr', 'status', 'user', 'route', 'flight_date', 'cabin', 'round_trip',
                    'passenger_count', 'total_price', 'card', 'created_at']
    list_display_links = ['pnr']
    list_filter = ['status', 'cabin', 'flight__airline', 'created_at']
    search_fields = ['pnr', 'user__email', 'user__first_name', 'user__last_name',
                     'passengers__first_name', 'passengers__last_name', 'passengers__passport']
    date_hierarchy = 'created_at'
    readonly_fields = ['pnr', 'created_at', 'paid_at', 'card_last4']
    list_select_related = ['user', 'flight__origin', 'flight__destination', 'flight__airline']
    inlines = [PassengerInline]
    actions = ['cancel_selected']

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(n_passengers=Count('passengers'))

    @admin.display(description='მარშრუტი')
    def route(self, obj):
        arrow = '⇄' if obj.return_flight_id else '→'
        return f'{obj.flight.origin.name} {arrow} {obj.flight.destination.name}'

    @admin.display(description='გაფრენა', ordering='flight__departure_time')
    def flight_date(self, obj):
        return obj.flight.departure_time.strftime('%d.%m.%Y %H:%M')

    @admin.display(description='ორმხრივი', boolean=True)
    def round_trip(self, obj):
        return obj.return_flight_id is not None

    @admin.display(description='მგზავრი')
    def passenger_count(self, obj):
        # ორმხრივზე თითო მგზავრი ორჯერ ინახება (ორივე ფრენაზე)
        return obj.n_passengers // (2 if obj.return_flight_id else 1)

    @admin.display(description='ბარათი')
    def card(self, obj):
        return f'•••• {obj.card_last4}' if obj.card_last4 else '—'

    @admin.action(description='არჩეული ჯავშნების გაუქმება')
    def cancel_selected(self, request, queryset):
        n = queryset.exclude(status=Booking.Status.CANCELLED).update(status=Booking.Status.CANCELLED)
        self.message_user(request, f'გაუქმდა {n} ჯავშანი')


@admin.register(Passenger)
class PassengerAdmin(admin.ModelAdmin):
    list_display = ['last_name', 'first_name', 'passport', 'seat', 'flight', 'booking', 'checked_in']
    list_filter = ['checked_in', 'booking__status']
    search_fields = ['first_name', 'last_name', 'passport', 'booking__pnr']
    list_select_related = ['flight', 'booking']


admin.site.register(Favorite)
