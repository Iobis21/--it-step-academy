import random
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone

# ===== სალონის განლაგება =====
# ბიზნესი: 1-3 რიგი, 4 ადგილი რიგში (A C | D F)
# ეკონომი: 4-15 რიგი, 6 ადგილი რიგში (A B C | D E F)
BUSINESS_ROWS = 3
TOTAL_ROWS = 15
EXIT_ROW = 9  # საავარიო გასასვლელი (ფრთებთან)

# ===== ბარგი =====
PERSONAL_ITEM_SIZE = '40×30×20 სმ'
MAX_EXTRA_CHECKED = 3

# გადახდისთვის ადგილი 15 წუთით ინახება
PAYMENT_MINUTES = 15


def seat_letters(row):
    """რიგში რომელი ადგილებია (მარცხენა მხარე, მარჯვენა მხარე)."""
    if row <= BUSINESS_ROWS:
        return 'AC', 'DF'
    return 'ABC', 'DEF'


def all_seats():
    """თვითმფრინავის ყველა ადგილის სია, მაგ: ['1A', '1C', ..., '15F']"""
    seats = []
    for row in range(1, TOTAL_ROWS + 1):
        left, right = seat_letters(row)
        for letter in left + right:
            seats.append(str(row) + letter)
    return seats


def generate_pnr(model):
    """6-სიმბოლოიანი უნიკალური ბილეთის ნომერი (0/O და 1/I გარეშე, რომ არ აგერიოს)."""
    letters = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'
    while True:
        code = ''
        for i in range(6):
            code += random.choice(letters)
        if not model.objects.filter(pnr=code).exists():
            return code


class City(models.Model):
    name = models.CharField('სახელი', max_length=100, unique=True)
    airport_code = models.CharField('აეროპორტის კოდი', max_length=3, unique=True)
    image_url = models.URLField('სურათი', blank=True)

    class Meta:
        verbose_name = 'ქალაქი'
        verbose_name_plural = 'ქალაქები'
        ordering = ['name']

    def __str__(self):
        return f'{self.name} ({self.airport_code})'


class Airline(models.Model):
    name = models.CharField('სახელი', max_length=100, unique=True)
    code = models.CharField('კოდი', max_length=2, unique=True)
    low_cost = models.BooleanField('ლოუქოსტერი', default=False,
                                   help_text='ლოუქოსტერის ეკონომ ბილეთში შედის მხოლოდ პირადი ნივთი')

    class Meta:
        verbose_name = 'ავიაკომპანია'
        verbose_name_plural = 'ავიაკომპანიები'
        ordering = ['name']

    def __str__(self):
        return self.name


class Flight(models.Model):
    flight_number = models.CharField('ფრენის ნომერი', max_length=10)
    airline = models.ForeignKey(Airline, on_delete=models.PROTECT, related_name='flights', verbose_name='ავიაკომპანია')
    origin = models.ForeignKey(City, on_delete=models.PROTECT, related_name='departures', verbose_name='საიდან')
    destination = models.ForeignKey(City, on_delete=models.PROTECT, related_name='arrivals', verbose_name='სად')
    departure_time = models.DateTimeField('გაფრენა')
    arrival_time = models.DateTimeField('ჩაფრენა')
    stops = models.PositiveSmallIntegerField('გადაჯდომა', default=0)
    economy_price = models.DecimalField('ეკონომი ფასი', max_digits=8, decimal_places=2)
    business_price = models.DecimalField('ბიზნეს ფასი', max_digits=8, decimal_places=2)

    class Meta:
        verbose_name = 'ფრენა'
        verbose_name_plural = 'ფრენები'
        ordering = ['departure_time']

    def __str__(self):
        return f'{self.flight_number}: {self.origin.name} → {self.destination.name}'

    # ----- დრო -----
    @property
    def duration_minutes(self):
        seconds = (self.arrival_time - self.departure_time).total_seconds()
        return int(seconds // 60)

    @property
    def duration_display(self):
        hours = self.duration_minutes // 60
        minutes = self.duration_minutes % 60
        if hours == 0:
            return f'{minutes}წთ'
        if minutes == 0:
            return f'{hours}სთ'
        return f'{hours}სთ {minutes}წთ'

    def is_valid_return_for(self, outbound):
        """არის თუ არა ეს ფრენა outbound ფრენის დაბრუნება (უკუ მარშრუტი, ჩაფრენის შემდეგ)."""
        same_route = self.origin_id == outbound.destination_id and self.destination_id == outbound.origin_id
        is_later = self.departure_time > outbound.arrival_time
        return same_route and is_later

    # ----- ფასი და კლასი -----
    def price_for(self, cabin):
        if cabin == 'business':
            return self.business_price
        return self.economy_price

    def cabin_of(self, seat):
        """ადგილის ნომრიდან (მაგ. '12C') კლასის გაგება."""
        row = int(seat[:-1])
        if row <= BUSINESS_ROWS:
            return 'business'
        return 'economy'

    # ----- ბარგი -----
    def baggage(self, cabin):
        """რა შედის ბილეთში და რა ღირს დამატებითი ბარგი (ერთ მგზავრზე)."""
        if cabin == 'business':
            return {'cabin_bags': 2, 'cabin_kg': 8, 'checked_bags': 2, 'checked_kg': 32,
                    'extra_cabin_price': 0, 'extra_checked_price': 199}
        if self.airline.low_cost:
            return {'cabin_bags': 0, 'cabin_kg': 10, 'checked_bags': 0, 'checked_kg': 20,
                    'extra_cabin_price': 49, 'extra_checked_price': 99}
        return {'cabin_bags': 1, 'cabin_kg': 8, 'checked_bags': 1, 'checked_kg': 23,
                'extra_cabin_price': 0, 'extra_checked_price': 129}

    def baggage_info(self):
        return {'economy': self.baggage('economy'), 'business': self.baggage('business')}

    def extras_price(self, cabin, extra_cabin_bag, extra_checked):
        """დამატებითი ბარგის ფასი ერთ მგზავრზე."""
        bag = self.baggage(cabin)
        price = extra_checked * bag['extra_checked_price']
        # ხელბარგს ვიხდით მხოლოდ მაშინ, თუ ბილეთში არ შედის
        if extra_cabin_bag and bag['cabin_bags'] == 0:
            price += bag['extra_cabin_price']
        return price

    # ----- ადგილები -----
    @property
    def seats_total(self):
        return len(all_seats())

    def taken_seats(self):
        """დაკავებული ადგილები: გადახდილი ჯავშნები + გადაუხდელი, რომლის 15 წუთიც ჯერ არ გასულა."""
        deadline = timezone.now() - timedelta(minutes=PAYMENT_MINUTES)
        taken = set()
        for p in Passenger.objects.filter(flight=self).select_related('booking'):
            status = p.booking.status
            if status == 'active':
                taken.add(p.seat)
            elif status == 'pending' and p.booking.created_at >= deadline:
                taken.add(p.seat)
        return taken

    def seats_left(self):
        return self.seats_total - len(self.taken_seats())

    def seat_map(self):
        """თვითმფრინავის სქემა შაბლონისთვის: ბიზნესის და ეკონომის რიგები."""
        taken = self.taken_seats()
        business = []
        economy = []
        for number in range(1, TOTAL_ROWS + 1):
            left, right = seat_letters(number)
            row = {'number': number, 'exit': number == EXIT_ROW, 'left': [], 'right': []}
            for letter in left:
                seat = str(number) + letter
                row['left'].append((seat, letter, seat in taken))
            for letter in right:
                seat = str(number) + letter
                row['right'].append((seat, letter, seat in taken))
            if number <= BUSINESS_ROWS:
                business.append(row)
            else:
                economy.append(row)
        return {'business': business, 'economy': economy}


class Booking(models.Model):
    class Cabin(models.TextChoices):
        ECONOMY = 'economy', 'ეკონომი'
        BUSINESS = 'business', 'ბიზნესი'

    class Status(models.TextChoices):
        PENDING = 'pending', 'გადასახდელი'
        ACTIVE = 'active', 'გადახდილი'
        CANCELLED = 'cancelled', 'გაუქმებული'

    # user ცარიელია, თუ ბილეთი რეგისტრაციის გარეშე (სტუმრად) იყიდა
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='bookings',
                             null=True, blank=True)
    contact_email = models.EmailField('საკონტაქტო ელ-ფოსტა', blank=True)
    contact_phone = models.CharField('საკონტაქტო ტელეფონი', max_length=20, blank=True)
    pnr =models.CharField('ჯავშნის კოდი', max_length=6, unique=True, null=True, blank=True)
    flight = models.ForeignKey(Flight, on_delete=models.PROTECT, related_name='bookings')
    return_flight = models.ForeignKey(
        Flight, on_delete=models.PROTECT, related_name='return_bookings',
        null=True, blank=True, verbose_name='დაბრუნების ფრენა',
    )
    cabin = models.CharField('კლასი', max_length=10, choices=Cabin.choices)
    total_price = models.DecimalField('ჯამური ფასი', max_digits=10, decimal_places=2)
    baggage_price = models.DecimalField('დამატებითი ბარგის ფასი', max_digits=10, decimal_places=2, default=0)
    status = models.CharField('სტატუსი', max_length=10, choices=Status.choices, default=Status.ACTIVE)
    created_at = models.DateTimeField('შექმნილია', auto_now_add=True)
    paid_at = models.DateTimeField('გადახდილია', null=True, blank=True)
    card_last4 = models.CharField('ბარათის ბოლო 4 ციფრი', max_length=4, blank=True)

    class Meta:
        verbose_name = 'ჯავშანი'
        verbose_name_plural = 'ჯავშნები'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.pnr} {self.contact_email} — {self.flight}'

    def save(self, *args, **kwargs):
        # ახალ ჯავშანს ავტომატურად ვანიჭებთ ბილეთის ნომერს
        if not self.pnr:
            self.pnr = generate_pnr(Booking)
        super().save(*args, **kwargs)

    @property
    def payment_expired(self):
        deadline = timezone.now() - timedelta(minutes=PAYMENT_MINUTES)
        return self.status == 'pending' and self.created_at < deadline

    @property
    def is_round_trip(self):
        return self.return_flight_id is not None

    @property
    def is_checked_in(self):
        for p in self.passengers.all():
            if not p.checked_in:
                return False
        return True

    @property
    def can_check_in(self):
        return self.status == 'active' and self.flight.departure_time > timezone.now()

    def outbound_passengers(self):
        return self.passengers.filter(flight_id=self.flight_id)

    def return_passengers(self):
        return self.passengers.filter(flight_id=self.return_flight_id)


class Passenger(models.Model):
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='passengers')
    flight = models.ForeignKey(Flight, on_delete=models.CASCADE, related_name='passengers')
    first_name = models.CharField('სახელი', max_length=50)
    last_name = models.CharField('გვარი', max_length=50)
    passport = models.CharField('პასპორტი / პირადი ნომერი', max_length=20)
    seat = models.CharField('ადგილი', max_length=4)
    checked_in = models.BooleanField('რეგისტრაცია გავლილია', default=False)
    extra_cabin_bag = models.BooleanField('დამატებითი ხელბარგი', default=False)
    extra_checked_bags = models.PositiveSmallIntegerField('დამატებითი ჩემოდანი', default=0)

    class Meta:
        verbose_name = 'მგზავრი'
        verbose_name_plural = 'მგზავრები'

    def __str__(self):
        return f'{self.first_name} {self.last_name} ({self.seat})'

    def baggage_lines(self):
        """ბილეთზე საჩვენებელი ბარგი: რაც შედის + რაც დამატებით იყიდა."""
        bag = self.flight.baggage(self.booking.cabin)

        cabin_bags = bag['cabin_bags']
        if cabin_bags == 0 and self.extra_cabin_bag:
            cabin_bags = 1
        checked = bag['checked_bags'] + self.extra_checked_bags

        lines = [f'პირადი ნივთი ({PERSONAL_ITEM_SIZE})']
        if cabin_bags > 0:
            lines.append(f'ხელბარგი {cabin_bags} × {bag["cabin_kg"]} კგ')
        if checked > 0:
            lines.append(f'ჩემოდანი {checked} × {bag["checked_kg"]} კგ')
        return lines


class Favorite(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='favorites')
    flight = models.ForeignKey(Flight, on_delete=models.CASCADE, related_name='favorited_by')

    class Meta:
        verbose_name = 'შენახული ფრენა'
        verbose_name_plural = 'შენახული ფრენები'
        constraints = [models.UniqueConstraint(fields=['user', 'flight'], name='unique_favorite')]
