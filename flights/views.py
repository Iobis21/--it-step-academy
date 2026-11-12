from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import FlightSearchForm
from .models import Booking, Favorite, Flight, Passenger

MAX_PASSENGERS = 6


def _upcoming():
    return Flight.objects.select_related('airline', 'origin', 'destination').filter(
        departure_time__gt=timezone.now()
    )


def home(request):
    cheapest = _upcoming().order_by('economy_price')[:6]
    return render(request, 'flights/home.html', {'form': FlightSearchForm(), 'flights': cheapest})


def search(request):
    form = FlightSearchForm(request.GET or None)
    flights = _upcoming()
    if form.is_valid():
        d = form.cleaned_data
        if d['origin']:
            flights = flights.filter(origin=d['origin'])
        if d['destination']:
            flights = flights.filter(destination=d['destination'])
        if d['date']:
            flights = flights.filter(departure_time__date=d['date'])
        if d['airline']:
            flights = flights.filter(airline=d['airline'])
        if d['max_price']:
            flights = flights.filter(economy_price__lte=d['max_price'])
        if d['direct_only']:
            flights = flights.filter(stops=0)
        flights = flights.order_by(d['sort'] or 'departure_time')
    return render(request, 'flights/search.html', {'form': form, 'flights': flights})


def flight_detail(request, pk):
    flight = get_object_or_404(Flight.objects.select_related('airline', 'origin', 'destination'), pk=pk)
    is_favorite = request.user.is_authenticated and Favorite.objects.filter(user=request.user, flight=flight).exists()
    return render(request, 'flights/flight_detail.html', {
        'flight': flight,
        'seat_map': flight.seat_map(),
        'is_favorite': is_favorite,
        'max_passengers': MAX_PASSENGERS,
    })


@login_required
@require_POST
def book(request, pk):
    flight = get_object_or_404(Flight, pk=pk)
    seats = request.POST.getlist('seat')

    def fail(msg):
        messages.error(request, msg)
        return redirect('flight_detail', pk=pk)

    if flight.departure_time <= timezone.now():
        return fail('ეს ფრენა უკვე შესრულდა')
    if not seats:
        return fail('აირჩიე მინიმუმ ერთი ადგილი')
    if len(seats) > MAX_PASSENGERS or len(set(seats)) != len(seats):
        return fail(f'ერთ ჯავშანზე მაქსიმუმ {MAX_PASSENGERS} მგზავრია')

    cabins = {flight.cabin_of(s) for s in seats}
    if len(cabins) != 1:
        return fail('ყველა ადგილი ერთი კლასიდან უნდა იყოს')
    cabin = cabins.pop()

    passengers = []
    for s in seats:
        first = request.POST.get(f'first_name_{s}', '').strip()
        last = request.POST.get(f'last_name_{s}', '').strip()
        passport = request.POST.get(f'passport_{s}', '').strip()
        if not (first and last and passport):
            return fail('შეავსე ყველა მგზავრის მონაცემები')
        passengers.append((s, first, last, passport))

    with transaction.atomic():
        if flight.taken_seats() & set(seats):
            return fail('არჩეული ადგილი უკვე დაკავებულია, აირჩიე სხვა')
        booking = Booking.objects.create(
            user=request.user,
            flight=flight,
            cabin=cabin,
            total_price=flight.price_for(cabin) * len(seats),
        )
        Passenger.objects.bulk_create([
            Passenger(booking=booking, flight=flight, seat=s, first_name=f, last_name=l, passport=p)
            for s, f, l, p in passengers
        ])

    messages.success(request, f'ჯავშანი #{booking.pk} წარმატებით შეიქმნა!')
    return redirect('profile')


@login_required
@require_POST
def cancel_booking(request, pk):
    booking = get_object_or_404(Booking, pk=pk, user=request.user)
    if booking.status == Booking.Status.ACTIVE:
        booking.status = Booking.Status.CANCELLED
        booking.save(update_fields=['status'])
        messages.info(request, f'ჯავშანი #{booking.pk} გაუქმდა')
    return redirect('profile')


@login_required
@require_POST
def toggle_favorite(request, pk):
    flight = get_object_or_404(Flight, pk=pk)
    fav, created = Favorite.objects.get_or_create(user=request.user, flight=flight)
    if not created:
        fav.delete()
    return redirect('flight_detail', pk=pk)


@login_required
def profile(request):
    bookings = (
        request.user.bookings.select_related('flight__airline', 'flight__origin', 'flight__destination')
        .prefetch_related('passengers')
    )
    favorites = _upcoming().filter(favorited_by__user=request.user)
    return render(request, 'flights/profile.html', {'bookings': bookings, 'favorites': favorites})
