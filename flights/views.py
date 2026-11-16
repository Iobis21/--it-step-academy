from datetime import date, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import CheckInForm, FlightSearchForm, PaymentForm
from .models import (
    MAX_EXTRA_CHECKED, PAYMENT_MINUTES, PERSONAL_ITEM_SIZE,
    Booking, Favorite, Flight, Passenger, all_seats,
)

MAX_PASSENGERS = 6


def upcoming_flights():
    """მომავალი ფრენები (უკვე შესრულებულები არ გვაინტერესებს)."""
    return Flight.objects.filter(departure_time__gt=timezone.now())


def get_cabin(value):
    if value == 'business':
        return 'business'
    return 'economy'


# ===================== მთავარი და ძიება =====================

def home(request):
    cheapest = upcoming_flights().order_by('economy_price')[:6]
    return render(request, 'flights/home.html', {'form': FlightSearchForm(), 'flights': cheapest})


def search(request):
    form = FlightSearchForm(request.GET or None)
    flights = upcoming_flights()
    cabin = get_cabin(request.GET.get('cabin'))
    link_suffix = '?cabin=' + cabin

    if form.is_valid():
        data = form.cleaned_data
        if data['origin']:
            flights = flights.filter(origin=data['origin'])
        if data['destination']:
            flights = flights.filter(destination=data['destination'])
        if data['date']:
            flights = flights.filter(departure_time__date=data['date'])
        if data['airline']:
            flights = flights.filter(airline=data['airline'])
        if data['direct_only']:
            flights = flights.filter(stops=0)

        # ფასის ფილტრი და დალაგება არჩეული კლასის ფასით
        if data['max_price']:
            if cabin == 'business':
                flights = flights.filter(business_price__lte=data['max_price'])
            else:
                flights = flights.filter(economy_price__lte=data['max_price'])

        sort = data['sort'] or 'departure_time'
        if cabin == 'business':
            sort = sort.replace('economy_price', 'business_price')
        flights = flights.order_by(sort)

        if data['trip_type'] == 'return':
            link_suffix += '&return_date=' + data['return_date'].isoformat()
    elif form.is_bound:
        flights = flights.none()

    return render(request, 'flights/search.html', {
        'form': form,
        'flights': flights,
        'is_return': form.is_return,
        'link_suffix': link_suffix,
        'cabin': cabin,
    })


# ===================== ფრენის გვერდი =====================

def find_return_flights(flight, return_date):
    """დაბრუნების ფრენები არჩეულ დღეს. თუ არ არის — ახლო დღეებში (±3 დღე)."""
    flights = upcoming_flights().filter(
        origin=flight.destination,
        destination=flight.origin,
        departure_time__gt=flight.arrival_time,
    ).order_by('departure_time')

    same_day = flights.filter(departure_time__date=return_date)
    if same_day.exists():
        return same_day, True

    start = return_date - timedelta(days=3)
    end = return_date + timedelta(days=3)
    return flights.filter(departure_time__date__range=(start, end)), False


def flight_detail(request, pk):
    flight = get_object_or_404(Flight, pk=pk)
    cabin = get_cabin(request.GET.get('cabin'))

    is_favorite = False
    if request.user.is_authenticated:
        is_favorite = Favorite.objects.filter(user=request.user, flight=flight).exists()

    context = {
        'flight': flight,
        'cabin': cabin,
        'bag_eco': flight.baggage('economy'),
        'bag_bus': flight.baggage('business'),
        'personal_item_size': PERSONAL_ITEM_SIZE,
        'max_extra_checked': MAX_EXTRA_CHECKED,
        'seat_map': flight.seat_map(),
        'max_passengers': MAX_PASSENGERS,
        'is_favorite': is_favorite,
    }

    return_id = request.GET.get('return')
    return_date = request.GET.get('return_date')

    if return_id:
        # ორმხრივი: დაბრუნების ფრენა უკვე არჩეულია
        return_flight = get_object_or_404(Flight, pk=return_id)
        if not return_flight.is_valid_return_for(flight):
            messages.error(request, 'ეს დაბრუნების ფრენა არ შეესაბამება მარშრუტს')
            return redirect('flight_detail', pk=pk)
        context['return_flight'] = return_flight
        context['return_seat_map'] = return_flight.seat_map()

    elif return_date:
        # ორმხრივი: ჯერ დაბრუნების ფრენა უნდა აირჩიოს
        try:
            return_date = date.fromisoformat(return_date)
        except ValueError:
            return redirect('flight_detail', pk=pk)
        options, exact = find_return_flights(flight, return_date)
        context['choosing_return'] = True
        context['return_date'] = return_date
        context['return_options'] = options
        context['return_exact'] = exact
        context['link_base'] = f'/flights/{flight.pk}/?cabin={cabin}&return='

    return render(request, 'flights/flight_detail.html', context)


# ===================== დაჯავშნა =====================

def read_passengers(request, seats):
    """ფორმიდან მგზავრების მონაცემების წაკითხვა. თუ რამე აკლია — აბრუნებს None-ს."""
    passengers = []
    for seat in seats:
        first_name = request.POST.get('first_name_' + seat, '').strip()
        last_name = request.POST.get('last_name_' + seat, '').strip()
        passport = request.POST.get('passport_' + seat, '').strip()
        if not first_name or not last_name or not passport:
            return None

        try:
            checked = int(request.POST.get('checked_' + seat) or 0)
        except ValueError:
            checked = 0
        if checked < 0 or checked > MAX_EXTRA_CHECKED:
            return None

        passengers.append({
            'first_name': first_name,
            'last_name': last_name,
            'passport': passport,
            'cabin_bag': request.POST.get('cabin_bag_' + seat) == '1',
            'checked': checked,
        })
    return passengers


def check_seats(flight, return_flight, seats, return_seats):
    """ადგილების შემოწმება. აბრუნებს (კლასი, შეცდომა)."""
    if not seats:
        return None, 'აირჩიე მინიმუმ ერთი ადგილი'
    if len(seats) > MAX_PASSENGERS or len(set(seats)) != len(seats):
        return None, f'ერთ ჯავშანზე მაქსიმუმ {MAX_PASSENGERS} მგზავრია'

    valid_seats = all_seats()
    for seat in seats + return_seats:
        if seat not in valid_seats:
            return None, 'ასეთი ადგილი თვითმფრინავში არ არსებობს'

    cabins = set()
    for seat in seats:
        cabins.add(flight.cabin_of(seat))

    if return_flight:
        if not return_flight.is_valid_return_for(flight):
            return None, 'დაბრუნების ფრენა არ შეესაბამება მარშრუტს'
        if len(return_seats) != len(seats) or len(set(return_seats)) != len(return_seats):
            return None, 'დაბრუნების ფრენაზეც იმდენივე ადგილი აირჩიე, რამდენი მგზავრიცაა'
        for seat in return_seats:
            cabins.add(return_flight.cabin_of(seat))

    if len(cabins) != 1:
        return None, 'ყველა ადგილი ერთი კლასიდან უნდა იყოს'

    # დაკავებული ხომ არ არის?
    taken = flight.taken_seats()
    for seat in seats:
        if seat in taken:
            return None, f'ადგილი {seat} უკვე დაკავებულია, აირჩიე სხვა'
    if return_flight:
        taken = return_flight.taken_seats()
        for seat in return_seats:
            if seat in taken:
                return None, f'დაბრუნების ფრენაზე ადგილი {seat} უკვე დაკავებულია'

    return cabins.pop(), None


def save_passengers(booking, flight, seats, passengers, cabin):
    for seat, p in zip(seats, passengers):
        # ხელბარგს ვინახავთ მხოლოდ თუ ბილეთში არ შედის (მაშინ ფასიანია)
        cabin_bag = p['cabin_bag'] and flight.baggage(cabin)['cabin_bags'] == 0
        Passenger.objects.create(
            booking=booking,
            flight=flight,
            seat=seat,
            first_name=p['first_name'],
            last_name=p['last_name'],
            passport=p['passport'],
            extra_cabin_bag=cabin_bag,
            extra_checked_bags=p['checked'],
        )


@login_required
@require_POST
def book(request, pk):
    flight = get_object_or_404(Flight, pk=pk)
    seats = request.POST.getlist('seat')
    return_seats = request.POST.getlist('return_seat')

    return_flight = None
    if request.POST.get('return_flight'):
        return_flight = get_object_or_404(Flight, pk=request.POST['return_flight'])

    # შეცდომის შემთხვევაში ამავე გვერდზე ვბრუნდებით
    back_url = f'/flights/{pk}/?cabin=' + get_cabin(request.POST.get('cabin'))
    if return_flight:
        back_url += f'&return={return_flight.pk}'

    if flight.departure_time <= timezone.now():
        messages.error(request, 'ეს ფრენა უკვე შესრულდა')
        return redirect(back_url)

    cabin, error = check_seats(flight, return_flight, seats, return_seats)
    if error:
        messages.error(request, error)
        return redirect(back_url)

    passengers = read_passengers(request, seats)
    if passengers is None:
        messages.error(request, 'შეავსე ყველა მგზავრის მონაცემები სწორად')
        return redirect(back_url)

    # ფასის დათვლა: ბილეთები + დამატებითი ბარგი
    flights = [flight]
    if return_flight:
        flights.append(return_flight)

    ticket_price = 0
    baggage_price = 0
    for f in flights:
        ticket_price += f.price_for(cabin) * len(seats)
        for p in passengers:
            baggage_price += f.extras_price(cabin, p['cabin_bag'], p['checked'])

    booking = Booking.objects.create(
        user=request.user,
        flight=flight,
        return_flight=return_flight,
        cabin=cabin,
        total_price=ticket_price + baggage_price,
        baggage_price=baggage_price,
        status='pending',
    )
    save_passengers(booking, flight, seats, passengers, cabin)
    if return_flight:
        save_passengers(booking, return_flight, return_seats, passengers, cabin)

    allow_ticket(request, booking)
    return redirect('pay', pnr=booking.pnr)


# ===================== გადახდა =====================

def pay(request, pnr):
    booking = get_ticket(request, pnr)
    if booking is None:
        return redirect('checkin')
    if booking.status != 'pending':
        return redirect('ticket', pnr=pnr)

    if booking.payment_expired:
        booking.status = 'cancelled'
        booking.save()
        messages.error(request, f'გადახდის დრო ({PAYMENT_MINUTES} წთ) ამოიწურა — ჯავშანი გაუქმდა')
        return redirect('flight_detail', pk=booking.flight_id)

    form = PaymentForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        booking.status = 'active'
        booking.paid_at = timezone.now()
        booking.card_last4 = form.cleaned_data['card_number'][-4:]  # ვინახავთ მხოლოდ ბოლო 4 ციფრს
        booking.save()
        messages.success(request, f'გადახდა წარმატებულია! ბილეთის ნომერი: {booking.pnr}')
        return redirect('ticket', pnr=pnr)

    deadline = booking.created_at + timedelta(minutes=PAYMENT_MINUTES)
    return render(request, 'flights/pay.html', {'booking': booking, 'form': form, 'deadline': deadline})


# ===================== ბილეთი: ნახვა, რეგისტრაცია, დაბრუნება =====================

def allow_ticket(request, booking):
    """სესიაში ვიმახსოვრებთ, რომ ამ ბილეთის ნახვის უფლება აქვს."""
    tickets = request.session.get('tickets', [])
    if booking.pnr not in tickets:
        tickets.append(booking.pnr)
    request.session['tickets'] = tickets


def get_ticket(request, pnr):
    """ბილეთს ხედავს მფლობელი, ან ვინც ბილეთის ნომერი + გვარი სწორად შეიყვანა."""
    booking = get_object_or_404(Booking, pnr=pnr)
    is_owner = request.user.is_authenticated and booking.user == request.user
    if is_owner or pnr in request.session.get('tickets', []):
        return booking
    return None


def checkin(request):
    form = CheckInForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        booking = Booking.objects.filter(
            pnr=form.cleaned_data['pnr'],
            passengers__last_name__iexact=form.cleaned_data['last_name'].strip(),
        ).first()
        if booking:
            allow_ticket(request, booking)
            return redirect('ticket', pnr=booking.pnr)
        form.add_error(None, 'ბილეთი ვერ მოიძებნა. შეამოწმე ბილეთის ნომერი და გვარი.')
    return render(request, 'flights/checkin.html', {'form': form})


def ticket(request, pnr):
    booking = get_ticket(request, pnr)
    if booking is None:
        messages.error(request, 'ბილეთის სანახავად შეიყვანე ბილეთის ნომერი და გვარი')
        return redirect('checkin')
    if booking.status == 'pending':
        return redirect('pay', pnr=pnr)

    legs = [(booking.flight, booking.outbound_passengers())]
    if booking.return_flight:
        legs.append((booking.return_flight, booking.return_passengers()))
    return render(request, 'flights/ticket.html', {'booking': booking, 'legs': legs})


@require_POST
def do_checkin(request, pnr):
    booking = get_ticket(request, pnr)
    if booking is None:
        return redirect('checkin')
    if booking.can_check_in:
        booking.passengers.update(checked_in=True)
        messages.success(request, 'რეგისტრაცია გავლილია! ჩასხდომის ბილეთი მზადაა ✈')
    else:
        messages.error(request, 'ამ ჯავშანზე რეგისტრაცია შეუძლებელია (გაუქმებულია ან ფრენა შესრულდა)')
    return redirect('ticket', pnr=pnr)


@require_POST
def cancel_ticket(request, pnr):
    """ბილეთის დაბრუნება ბილეთის ნომრით."""
    booking = get_ticket(request, pnr)
    if booking is None:
        return redirect('checkin')

    if booking.status == 'cancelled':
        messages.info(request, 'ბილეთი უკვე გაუქმებულია')
    elif booking.flight.departure_time <= timezone.now():
        messages.error(request, 'შესრულებული ფრენის ბილეთის დაბრუნება შეუძლებელია')
    else:
        booking.status = 'cancelled'
        booking.save()
        messages.info(request, f'ბილეთი {booking.pnr} გაუქმდა. თანხა ({booking.total_price:.0f} ₾) დაგიბრუნდებათ ბარათზე.')
    return redirect('ticket', pnr=pnr)


# ===================== პროფილი =====================

@login_required
@require_POST
def cancel_booking(request, pk):
    booking = get_object_or_404(Booking, pk=pk, user=request.user)
    if booking.status != 'cancelled':
        booking.status = 'cancelled'
        booking.save()
        messages.info(request, f'ჯავშანი {booking.pnr} გაუქმდა')
    return redirect('profile')


@login_required
@require_POST
def toggle_favorite(request, pk):
    flight = get_object_or_404(Flight, pk=pk)
    favorite = Favorite.objects.filter(user=request.user, flight=flight).first()
    if favorite:
        favorite.delete()
    else:
        Favorite.objects.create(user=request.user, flight=flight)
    return redirect('flight_detail', pk=pk)


@login_required
def profile(request):
    bookings = Booking.objects.filter(user=request.user)
    favorites = upcoming_flights().filter(favorited_by__user=request.user)
    return render(request, 'flights/profile.html', {'bookings': bookings, 'favorites': favorites})
