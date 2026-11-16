"""SkyBook REST API (მხოლოდ კითხვა) — პასუხები JSON ფორმატშია."""
from datetime import date

from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_GET

from .models import Airline, Booking, City, Flight

MAX_RESULTS = 100


def _error(message, status=400):
    return JsonResponse({'error': message}, status=status, json_dumps_params={'ensure_ascii': False})


def _json(data):
    return JsonResponse(data, safe=False, json_dumps_params={'ensure_ascii': False})


def _city(c):
    return {'code': c.airport_code, 'name': c.name}


def _flight(f, detail=False):
    data = {
        'id': f.id,
        'flight_number': f.flight_number,
        'airline': {'code': f.airline.code, 'name': f.airline.name, 'low_cost': f.airline.low_cost},
        'from': _city(f.origin),
        'to': _city(f.destination),
        'departure': timezone.localtime(f.departure_time).isoformat(),
        'arrival': timezone.localtime(f.arrival_time).isoformat(),
        'duration_minutes': f.duration_minutes,
        'stops': f.stops,
        'price': {'economy': float(f.economy_price), 'business': float(f.business_price), 'currency': 'GEL'},
    }
    if detail:
        taken = f.taken_seats()
        data['seats'] = {
            'total': f.seats_total,
            'available': f.seats_total - len(taken),
            'taken': sorted(taken, key=lambda s: (int(s[:-1]), s[-1])),
        }
        data['baggage'] = f.baggage_info()
    return data


@require_GET
def index(request):
    """API-ს დოკუმენტაცია."""
    return _json({
        'name': 'SkyBook API',
        'endpoints': {
            'GET /api/cities/': 'ქალაქები / აეროპორტები',
            'GET /api/airlines/': 'ავიაკომპანიები',
            'GET /api/flights/': 'ფრენების ძიება. პარამეტრები: from, to (აეროპორტის კოდი, მაგ. TBS), '
                                 'date (YYYY-MM-DD), airline (კოდი), max_price, direct (1), cabin (economy|business)',
            'GET /api/flights/<id>/': 'ერთი ფრენა: თავისუფალი/დაკავებული ადგილები და ბარგის პირობები',
            'GET /api/tickets/<ბილეთის ნომერი>/?last_name=...': 'ბილეთის შემოწმება (საჭიროა მგზავრის გვარი)',
        },
    })


@require_GET
def cities(request):
    return _json([_city(c) for c in City.objects.all()])


@require_GET
def airlines(request):
    return _json([{'code': a.code, 'name': a.name, 'low_cost': a.low_cost} for a in Airline.objects.all()])


@require_GET
def flights(request):
    qs = Flight.objects.select_related('airline', 'origin', 'destination').filter(
        departure_time__gt=timezone.now()
    )
    p = request.GET
    if p.get('from'):
        qs = qs.filter(origin__airport_code__iexact=p['from'])
    if p.get('to'):
        qs = qs.filter(destination__airport_code__iexact=p['to'])
    if p.get('airline'):
        qs = qs.filter(airline__code__iexact=p['airline'])
    if p.get('date'):
        try:
            qs = qs.filter(departure_time__date=date.fromisoformat(p['date']))
        except ValueError:
            return _error('date უნდა იყოს ფორმატში YYYY-MM-DD')
    if p.get('direct') == '1':
        qs = qs.filter(stops=0)
    price_field = 'business_price' if p.get('cabin') == 'business' else 'economy_price'
    if p.get('max_price'):
        try:
            qs = qs.filter(**{f'{price_field}__lte': float(p['max_price'])})
        except ValueError:
            return _error('max_price უნდა იყოს რიცხვი')

    total = qs.count()
    results = [_flight(f) for f in qs.order_by('departure_time')[:MAX_RESULTS]]
    return _json({'count': total, 'returned': len(results), 'results': results})


@require_GET
def flight_detail(request, pk):
    f = get_object_or_404(Flight.objects.select_related('airline', 'origin', 'destination'), pk=pk)
    return _json(_flight(f, detail=True))


@require_GET
def ticket(request, pnr):
    last_name = request.GET.get('last_name', '').strip()
    if not last_name:
        return _error('მიუთითე პარამეტრი last_name')
    booking = (
        Booking.objects.filter(pnr=pnr.upper(), passengers__last_name__iexact=last_name)
        .select_related('flight__airline', 'flight__origin', 'flight__destination',
                        'return_flight__airline', 'return_flight__origin', 'return_flight__destination')
        .prefetch_related('passengers')
        .first()
    )
    if booking is None:
        return _error('ბილეთი ვერ მოიძებნა', status=404)

    def leg(flight, passengers):
        return {
            'flight': _flight(flight),
            'passengers': [
                {'first_name': p.first_name, 'last_name': p.last_name, 'seat': p.seat,
                 'checked_in': p.checked_in, 'baggage': p.baggage_lines()}
                for p in passengers
            ],
        }

    legs = [leg(booking.flight, booking.outbound_passengers())]
    if booking.return_flight:
        legs.append(leg(booking.return_flight, booking.return_passengers()))
    # პირადი/პასპორტის ნომერი და ბარათის მონაცემები API-ში არ გამოდის
    return _json({
        'ticket_number': booking.pnr,
        'status': booking.status,
        'cabin': booking.cabin,
        'round_trip': booking.is_round_trip,
        'total_price': float(booking.total_price),
        'currency': 'GEL',
        'legs': legs,
    })
