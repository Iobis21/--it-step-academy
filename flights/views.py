from datetime import date, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import CheckInForm, FlightSearchForm
from .models import Booking, Favorite, Flight, Passenger

MAX_PASSENGERS = 6


def _upcoming():
    return Flight.objects.select_related('airline', 'origin', 'destination').filter(
        departure_time__gt=timezone.now()
    )


def home(request):
    cheapest = _upcoming().order_by('economy_price')[:6]
    return render(request, 'flights/home.html', {'form': FlightSearchForm(), 'flights': cheapest})


def _cabin(value):
    return 'business' if value == 'business' else 'economy'


def search(request):
    form = FlightSearchForm(request.GET or None)
    flights = _upcoming()
    cabin = _cabin(request.GET.get('cabin'))
    link_suffix = f'?cabin={cabin}'
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
        price_field = f'{cabin}_price'
        if d['max_price']:
            flights = flights.filter(**{f'{price_field}__lte': d['max_price']})
        if d['direct_only']:
            flights = flights.filter(stops=0)
        sort = (d['sort'] or 'departure_time').replace('economy_price', price_field)
        flights = flights.order_by(sort)
        if d['trip_type'] == FlightSearchForm.RETURN:
            link_suffix += f'&return_date={d["return_date"].isoformat()}'
    elif form.is_bound:
        flights = flights.none()
    return render(request, 'flights/search.html', {
        'form': form,
        'flights': flights,
        'is_return': form.is_return,
        'link_suffix': link_suffix,
        'cabin': cabin,
    })


def _return_options(flight, return_date):
    """დაბრუნების ფრენები არჩეულ თარიღზე; თუ არ არის — ±3 დღის ფარგლებში."""
    base = _upcoming().filter(
        origin=flight.destination,
        destination=flight.origin,
        departure_time__gt=flight.arrival_time,
    )
    exact = base.filter(departure_time__date=return_date).order_by('departure_time')
    if exact.exists():
        return exact, True
    nearby = base.filter(
        departure_time__date__range=(return_date - timedelta(days=3), return_date + timedelta(days=3))
    ).order_by('departure_time')
    return nearby, False


def flight_detail(request, pk):
    flight = get_object_or_404(Flight.objects.select_related('airline', 'origin', 'destination'), pk=pk)
    cabin = _cabin(request.GET.get('cabin'))
    context = {
        'flight': flight,
        'cabin': cabin,
        'seat_map': flight.seat_map(),
        'max_passengers': MAX_PASSENGERS,
        'is_favorite': request.user.is_authenticated
        and Favorite.objects.filter(user=request.user, flight=flight).exists(),
    }

    return_id = request.GET.get('return')
    return_date = request.GET.get('return_date')
    if return_id:
        return_flight = get_object_or_404(Flight.objects.select_related('airline', 'origin', 'destination'), pk=return_id)
        if not return_flight.is_valid_return_for(flight):
            messages.error(request, 'ეს დაბრუნების ფრენა არ შეესაბამება მარშრუტს')
            return redirect('flight_detail', pk=pk)
        context['return_flight'] = return_flight
        context['return_seat_map'] = return_flight.seat_map()
    elif return_date:
        try:
            parsed = date.fromisoformat(return_date)
        except ValueError:
            return redirect('flight_detail', pk=pk)
        options, exact = _return_options(flight, parsed)
        context.update({
            'choosing_return': True,
            'return_date': parsed,
            'return_options': options,
            'return_exact': exact,
            'link_base': f'/flights/{flight.pk}/?cabin={cabin}&return=',
        })
    return render(request, 'flights/flight_detail.html', context)


def _collect_passengers(request, seats):
    passengers = []
    for s in seats:
        first = request.POST.get(f'first_name_{s}', '').strip()
        last = request.POST.get(f'last_name_{s}', '').strip()
        passport = request.POST.get(f'passport_{s}', '').strip()
        if not (first and last and passport):
            return None
        passengers.append((first, last, passport))
    return passengers


@login_required
@require_POST
def book(request, pk):
    flight = get_object_or_404(Flight, pk=pk)
    seats = request.POST.getlist('seat')
    return_seats = request.POST.getlist('return_seat')
    return_flight = None
    if request.POST.get('return_flight'):
        return_flight = get_object_or_404(Flight, pk=request.POST['return_flight'])

    back_url = f'/flights/{pk}/?cabin={_cabin(request.POST.get("cabin"))}' + (
        f'&return={return_flight.pk}' if return_flight else ''
    )

    def fail(msg):
        messages.error(request, msg)
        return redirect(back_url)

    if flight.departure_time <= timezone.now():
        return fail('ეს ფრენა უკვე შესრულდა')
    if not seats:
        return fail('აირჩიე მინიმუმ ერთი ადგილი')
    if len(seats) > MAX_PASSENGERS or len(set(seats)) != len(seats):
        return fail(f'ერთ ჯავშანზე მაქსიმუმ {MAX_PASSENGERS} მგზავრია')
    if not set(seats + return_seats) <= Flight.all_seats():
        return fail('ასეთი ადგილი თვითმფრინავში არ არსებობს')

    cabins = {flight.cabin_of(s) for s in seats}
    if return_flight:
        if not return_flight.is_valid_return_for(flight):
            return fail('დაბრუნების ფრენა არ შეესაბამება მარშრუტს')
        if len(return_seats) != len(seats) or len(set(return_seats)) != len(return_seats):
            return fail('დაბრუნების ფრენაზეც იმდენივე ადგილი აირჩიე, რამდენი მგზავრიცაა')
        cabins |= {return_flight.cabin_of(s) for s in return_seats}
    if len(cabins) != 1:
        return fail('ყველა ადგილი ერთი კლასიდან უნდა იყოს')
    cabin = cabins.pop()

    passengers = _collect_passengers(request, seats)
    if passengers is None:
        return fail('შეავსე ყველა მგზავრის მონაცემები')

    total = flight.price_for(cabin) * len(seats)
    if return_flight:
        total += return_flight.price_for(cabin) * len(seats)

    with transaction.atomic():
        if flight.taken_seats() & set(seats):
            return fail('არჩეული ადგილი უკვე დაკავებულია, აირჩიე სხვა')
        if return_flight and return_flight.taken_seats() & set(return_seats):
            return fail('დაბრუნების ფრენაზე არჩეული ადგილი უკვე დაკავებულია')
        booking = Booking.objects.create(
            user=request.user, flight=flight, return_flight=return_flight, cabin=cabin, total_price=total,
        )
        rows = [
            Passenger(booking=booking, flight=flight, seat=s, first_name=f, last_name=l, passport=p)
            for s, (f, l, p) in zip(seats, passengers)
        ]
        if return_flight:
            rows += [
                Passenger(booking=booking, flight=return_flight, seat=s, first_name=f, last_name=l, passport=p)
                for s, (f, l, p) in zip(return_seats, passengers)
            ]
        Passenger.objects.bulk_create(rows)

    messages.success(request, f'ჯავშანი წარმატებით შეიქმნა! ჯავშნის კოდი: {booking.pnr}')
    _allow_ticket(request, booking)
    return redirect('ticket', pnr=booking.pnr)


# ===== ონლაინ რეგისტრაცია (check-in) და ბილეთის ნახვა =====

def _allow_ticket(request, booking):
    allowed = set(request.session.get('tickets', []))
    allowed.add(booking.pnr)
    request.session['tickets'] = sorted(allowed)


def _ticket_booking(request, pnr):
    """ბილეთის ნახვა შეუძლია მფლობელს ან მას, ვინც კოდი + გვარი სწორად შეიყვანა."""
    booking = get_object_or_404(
        Booking.objects.select_related(
            'user', 'flight__airline', 'flight__origin', 'flight__destination',
            'return_flight__airline', 'return_flight__origin', 'return_flight__destination',
        ).prefetch_related('passengers'),
        pnr=pnr,
    )
    is_owner = request.user.is_authenticated and booking.user_id == request.user.id
    if not (is_owner or pnr in request.session.get('tickets', [])):
        return None
    return booking


def checkin(request):
    form = CheckInForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        booking = Booking.objects.filter(
            pnr=form.cleaned_data['pnr'],
            passengers__last_name__iexact=form.cleaned_data['last_name'].strip(),
        ).first()
        if booking:
            _allow_ticket(request, booking)
            return redirect('ticket', pnr=booking.pnr)
        form.add_error(None, 'ჯავშანი ვერ მოიძებნა. შეამოწმე ჯავშნის კოდი და გვარი.')
    return render(request, 'flights/checkin.html', {'form': form})


def ticket(request, pnr):
    booking = _ticket_booking(request, pnr)
    if booking is None:
        messages.error(request, 'ბილეთის სანახავად შეიყვანე ჯავშნის კოდი და გვარი')
        return redirect('checkin')
    legs = [(booking.flight, booking.outbound_passengers())]
    if booking.return_flight:
        legs.append((booking.return_flight, booking.return_passengers()))
    return render(request, 'flights/ticket.html', {'booking': booking, 'legs': legs})


@require_POST
def do_checkin(request, pnr):
    booking = _ticket_booking(request, pnr)
    if booking is None:
        return redirect('checkin')
    if not booking.can_check_in:
        messages.error(request, 'ამ ჯავშანზე რეგისტრაცია შეუძლებელია (გაუქმებულია ან ფრენა შესრულდა)')
    else:
        booking.passengers.update(checked_in=True)
        messages.success(request, 'რეგისტრაცია გავლილია! ჩასხდომის ბილეთი მზადაა ✈')
    return redirect('ticket', pnr=pnr)


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
    related = ['airline', 'origin', 'destination']
    bookings = (
        request.user.bookings
        .select_related(*[f'flight__{r}' for r in related], *[f'return_flight__{r}' for r in related])
        .prefetch_related('passengers')
    )
    favorites = _upcoming().filter(favorited_by__user=request.user)
    return render(request, 'flights/profile.html', {'bookings': bookings, 'favorites': favorites})
