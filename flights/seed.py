"""
სატესტო ფრენების გენერაცია რეალისტური ფასებით და ხანგრძლივობით.

ფასი ითვლება მარშრუტის რეალური მანძილით (კმ) და ავიაკომპანიის ტიპით
(ლოუქოსტერი იაფია, პრემიუმ კომპანია — ძვირი). ფასები ლარშია, ცალმხრივი ბილეთი.
"""
import math
import random
from datetime import timedelta

from django.utils import timezone

# ქალაქი, აეროპორტის კოდი, სურათი, (განედი, გრძედი), საქართველოშია თუ არა
CITIES = [
    ('თბილისი', 'TBS', 'https://images.unsplash.com/photo-1565008576549-57569a49371d?w=800', (41.67, 44.95), True),
    ('ბათუმი', 'BUS', '/static/img/batumi.jpg', (41.61, 41.60), True),
    ('ქუთაისი', 'KUT', '/static/img/kutaisi.jpg', (42.18, 42.48), True),
    ('სტამბოლი', 'IST', 'https://images.unsplash.com/photo-1524231757912-21f4fe3a7200?w=800', (41.26, 28.74), False),
    ('პარიზი', 'CDG', 'https://images.unsplash.com/photo-1502602898657-3e91760cbb34?w=800', (49.01, 2.55), False),
    ('ლონდონი', 'LHR', 'https://images.unsplash.com/photo-1513635269975-59663e0ac1ad?w=800', (51.47, -0.45), False),
    ('რომი', 'FCO', 'https://images.unsplash.com/photo-1552832230-c0197dd311b5?w=800', (41.80, 12.25), False),
    ('დუბაი', 'DXB', 'https://images.unsplash.com/photo-1512453979798-5ea266f8880c?w=800', (25.25, 55.36), False),
    ('ბერლინი', 'BER', 'https://images.unsplash.com/photo-1560969184-10fe8719e047?w=800', (52.37, 13.50), False),
    ('ბარსელონა', 'BCN', 'https://images.unsplash.com/photo-1583422409516-2895a77efded?w=800', (41.30, 2.08), False),
]

# სახელი, კოდი, ფასის კოეფიციენტი
AIRLINES = [
    ('Georgian Airways', 'A9', 1.00),
    ('Turkish Airlines', 'TK', 1.15),
    ('Wizz Air', 'W6', 0.55),
    ('Pegasus', 'PC', 0.70),
    ('Lufthansa', 'LH', 1.35),
    ('Emirates', 'EK', 1.45),
    ('flydubai', 'FZ', 0.90),
]

# რომელი ავიაკომპანია რომელ საზღვარგარეთის აეროპორტში დაფრინავს
ROUTES = {
    'IST': ['A9', 'TK', 'PC'],
    'CDG': ['A9', 'TK', 'LH'],
    'LHR': ['A9', 'TK', 'LH'],
    'FCO': ['W6', 'TK', 'PC'],
    'DXB': ['FZ', 'EK', 'TK'],
    'BER': ['W6', 'LH', 'PC'],
    'BCN': ['W6', 'TK', 'PC'],
}
DOMESTIC_AIRLINE = 'A9'
CRUISE_SPEED_KMH = 780


def distance_km(a, b):
    """ორ წერტილს შორის მანძილი დედამიწის ზედაპირზე (ჰავერსინუსის ფორმულა)."""
    lat1, lon1, lat2, lon2 = map(math.radians, (*a, *b))
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    return 2 * 6371 * math.asin(math.sqrt(h))


def economy_price(km, airline_factor, stops, rnd):
    base = 70 + km * 0.21            # 300 კმ ≈ 135₾, 1700 კმ ≈ 430₾, 3500 კმ ≈ 800₾
    if stops:
        base *= 0.85                 # გადაჯდომით ფრენა უფრო იაფია
    base *= airline_factor
    base *= rnd.uniform(0.8, 1.3)    # მოთხოვნის მიხედვით ფასის მერყეობა
    return max(59, round(base / 5) * 5 - 1)  # მაგ. 349, 429


def duration_minutes(km, stops, rnd):
    minutes = km / CRUISE_SPEED_KMH * 60 + 30  # +30 წთ აფრენა/დაფრენა
    if stops:
        minutes += rnd.randint(90, 240)        # გადაჯდომის ლოდინი
    return int(round(minutes / 5) * 5)


def generate_flights(City, Airline, Flight, days=30, per_day=8, seed=42):
    rnd = random.Random(seed)
    coords = {code: (c, georgian) for _, code, _, c, georgian in CITIES}

    cities = {}
    for name, code, img, _, _ in CITIES:
        cities[code] = City.objects.update_or_create(airport_code=code, defaults={'name': name, 'image_url': img})[0]
    airlines = {}
    for name, code, factor in AIRLINES:
        airlines[code] = (Airline.objects.update_or_create(code=code, defaults={'name': name})[0], factor)

    georgian = [c for c, (_, g) in coords.items() if g]
    foreign = [c for c, (_, g) in coords.items() if not g]

    today = timezone.localtime().replace(hour=0, minute=0, second=0, microsecond=0)
    flights = []
    for day in range(1, days + 1):
        for _ in range(per_day):
            if rnd.random() < 0.15:
                # შიდა რეისი
                a, b = rnd.sample(georgian, 2)
                airline_code = DOMESTIC_AIRLINE
            else:
                a, b = rnd.choice(georgian), rnd.choice(foreign)
                airline_code = rnd.choice(ROUTES[b])
                if rnd.random() < 0.5:
                    a, b = b, a  # დაბრუნების რეისი

            airline, factor = airlines[airline_code]
            km = distance_km(coords[a][0], coords[b][0])
            # დუბაი/სტამბოლი პირდაპირია, ევროპა ზოგჯერ გადაჯდომით (არა ლოუქოსტერზე)
            stops = 1 if (km > 2000 and airline_code not in ('W6', 'A9') and rnd.random() < 0.4) else 0

            dep = today + timedelta(days=day, hours=rnd.randint(4, 23), minutes=rnd.choice([0, 15, 30, 45]))
            price = economy_price(km, factor, stops, rnd)
            flights.append(Flight(
                flight_number=f'{airline_code}{rnd.randint(100, 999)}',
                airline=airline,
                origin=cities[a],
                destination=cities[b],
                departure_time=dep,
                arrival_time=dep + timedelta(minutes=duration_minutes(km, stops, rnd)),
                stops=stops,
                economy_price=price,
                business_price=round(price * rnd.uniform(2.8, 3.5) / 10) * 10 - 1,
            ))
    Flight.objects.bulk_create(flights)
    return len(flights)
