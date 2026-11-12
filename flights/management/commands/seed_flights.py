import random
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from flights.models import Airline, City, Flight

CITIES = [
    ('თბილისი', 'TBS', 'https://images.unsplash.com/photo-1565008576549-57569a49371d?w=800'),
    ('ბათუმი', 'BUS', 'https://images.unsplash.com/photo-1597466765990-64ad1c35dafc?w=800'),
    ('ქუთაისი', 'KUT', 'https://images.unsplash.com/photo-1622037022824-0c71d511ef3c?w=800'),
    ('სტამბოლი', 'IST', 'https://images.unsplash.com/photo-1524231757912-21f4fe3a7200?w=800'),
    ('პარიზი', 'CDG', 'https://images.unsplash.com/photo-1502602898657-3e91760cbb34?w=800'),
    ('ლონდონი', 'LHR', 'https://images.unsplash.com/photo-1513635269975-59663e0ac1ad?w=800'),
    ('რომი', 'FCO', 'https://images.unsplash.com/photo-1552832230-c0197dd311b5?w=800'),
    ('დუბაი', 'DXB', 'https://images.unsplash.com/photo-1512453979798-5ea266f8880c?w=800'),
    ('ბერლინი', 'BER', 'https://images.unsplash.com/photo-1560969184-10fe8719e047?w=800'),
    ('ბარსელონა', 'BCN', 'https://images.unsplash.com/photo-1583422409516-2895a77efded?w=800'),
]

AIRLINES = [
    ('Georgian Airways', 'A9'),
    ('Turkish Airlines', 'TK'),
    ('Wizz Air', 'W6'),
    ('Pegasus', 'PC'),
    ('Lufthansa', 'LH'),
    ('Emirates', 'EK'),
]


class Command(BaseCommand):
    help = 'ბაზას ავსებს სატესტო ქალაქებით, ავიაკომპანიებით და ფრენებით'

    def add_arguments(self, parser):
        parser.add_argument('--days', type=int, default=30, help='რამდენი დღის ფრენები შეიქმნას')
        parser.add_argument('--per-day', type=int, default=8, help='ფრენების რაოდენობა დღეში')

    def handle(self, *args, days, per_day, **options):
        random.seed(42)
        cities = [
            City.objects.update_or_create(airport_code=code, defaults={'name': name, 'image_url': img})[0]
            for name, code, img in CITIES
        ]
        airlines = [
            Airline.objects.update_or_create(code=code, defaults={'name': name})[0]
            for name, code in AIRLINES
        ]

        Flight.objects.filter(bookings__isnull=True, departure_time__gt=timezone.now()).delete()

        today = timezone.localtime().replace(hour=0, minute=0, second=0, microsecond=0)
        flights = []
        for day in range(1, days + 1):
            for _ in range(per_day):
                origin, destination = random.sample(cities, 2)
                airline = random.choice(airlines)
                dep = today + timedelta(days=day, hours=random.randint(5, 22), minutes=random.choice([0, 15, 30, 45]))
                duration = timedelta(minutes=random.randint(60, 360))
                price = random.randint(120, 1000)
                flights.append(Flight(
                    flight_number=f'{airline.code}{random.randint(100, 999)}',
                    airline=airline,
                    origin=origin,
                    destination=destination,
                    departure_time=dep,
                    arrival_time=dep + duration,
                    stops=0 if random.random() < 0.65 else 1,
                    economy_price=price,
                    business_price=round(price * 2.6),
                ))
        Flight.objects.bulk_create(flights)
        self.stdout.write(self.style.SUCCESS(f'შეიქმნა {len(flights)} ფრენა'))
