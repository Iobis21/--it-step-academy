import secrets

from django.conf import settings
from django.db import models

# ჯავშნის კოდი — 6 სიმბოლო, დამაბნეველი სიმბოლოების (0/O, 1/I) გარეშე
PNR_ALPHABET = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'


def generate_pnr(model):
    while True:
        code = ''.join(secrets.choice(PNR_ALPHABET) for _ in range(6))
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

    class Meta:
        verbose_name = 'ავიაკომპანია'
        verbose_name_plural = 'ავიაკომპანიები'
        ordering = ['name']

    def __str__(self):
        return self.name


class Flight(models.Model):
    ROWS = 10
    SEAT_LETTERS = 'ABCDEF'
    BUSINESS_ROWS = 2

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

    @property
    def duration_minutes(self):
        return int((self.arrival_time - self.departure_time).total_seconds() // 60)

    def is_valid_return_for(self, outbound):
        """შეიძლება თუ არა ეს ფრენა იყოს `outbound`-ის დაბრუნების ფრენა."""
        return (
            self.origin_id == outbound.destination_id
            and self.destination_id == outbound.origin_id
            and self.departure_time > outbound.arrival_time
        )

    @property
    def duration_display(self):
        h, m = divmod(self.duration_minutes, 60)
        if not h:
            return f'{m}წთ'
        return f'{h}სთ {m}წთ' if m else f'{h}სთ'

    @property
    def seats_total(self):
        return self.ROWS * len(self.SEAT_LETTERS)

    def taken_seats(self):
        return set(
            Passenger.objects.filter(flight=self, booking__status=Booking.Status.ACTIVE)
            .values_list('seat', flat=True)
        )

    def seats_left(self):
        return self.seats_total - len(self.taken_seats())

    def cabin_of(self, seat):
        row = int(seat[:-1])
        return Booking.Cabin.BUSINESS if row <= self.BUSINESS_ROWS else Booking.Cabin.ECONOMY

    def price_for(self, cabin):
        return self.business_price if cabin == Booking.Cabin.BUSINESS else self.economy_price

    def seat_map(self):
        """აბრუნებს რიგების სიას: [(row, is_business, [(seat, taken), ...]), ...]"""
        taken = self.taken_seats()
        rows = []
        for r in range(1, self.ROWS + 1):
            seats = [(f'{r}{l}', f'{r}{l}' in taken) for l in self.SEAT_LETTERS]
            rows.append((r, r <= self.BUSINESS_ROWS, seats))
        return rows


class Booking(models.Model):
    class Cabin(models.TextChoices):
        ECONOMY = 'economy', 'ეკონომი'
        BUSINESS = 'business', 'ბიზნესი'

    class Status(models.TextChoices):
        ACTIVE = 'active', 'აქტიური'
        CANCELLED = 'cancelled', 'გაუქმებული'

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='bookings')
    pnr = models.CharField('ჯავშნის კოდი', max_length=6, unique=True, null=True, blank=True)
    flight = models.ForeignKey(Flight, on_delete=models.PROTECT, related_name='bookings')
    return_flight = models.ForeignKey(
        Flight, on_delete=models.PROTECT, related_name='return_bookings',
        null=True, blank=True, verbose_name='დაბრუნების ფრენა',
    )
    cabin = models.CharField('კლასი', max_length=10, choices=Cabin.choices)
    total_price = models.DecimalField('ჯამური ფასი', max_digits=10, decimal_places=2)
    status = models.CharField('სტატუსი', max_length=10, choices=Status.choices, default=Status.ACTIVE)
    created_at = models.DateTimeField('შექმნილია', auto_now_add=True)

    class Meta:
        verbose_name = 'ჯავშანი'
        verbose_name_plural = 'ჯავშნები'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.pnr or self.pk} {self.user} — {self.flight}'

    def save(self, *args, **kwargs):
        if not self.pnr:
            self.pnr = generate_pnr(Booking)
        super().save(*args, **kwargs)

    @property
    def is_checked_in(self):
        return all(p.checked_in for p in self.passengers.all())

    @property
    def can_check_in(self):
        from django.utils import timezone
        return self.status == self.Status.ACTIVE and self.flight.departure_time > timezone.now()

    @property
    def is_round_trip(self):
        return self.return_flight_id is not None

    def outbound_passengers(self):
        return [p for p in self.passengers.all() if p.flight_id == self.flight_id]

    def return_passengers(self):
        return [p for p in self.passengers.all() if p.flight_id == self.return_flight_id]


class Passenger(models.Model):
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='passengers')
    flight = models.ForeignKey(Flight, on_delete=models.CASCADE, related_name='passengers')
    first_name = models.CharField('სახელი', max_length=50)
    last_name = models.CharField('გვარი', max_length=50)
    passport = models.CharField('პასპორტი / პირადი ნომერი', max_length=20)
    seat = models.CharField('ადგილი', max_length=4)
    checked_in = models.BooleanField('რეგისტრაცია გავლილია', default=False)

    class Meta:
        verbose_name = 'მგზავრი'
        verbose_name_plural = 'მგზავრები'

    def __str__(self):
        return f'{self.first_name} {self.last_name} ({self.seat})'


class Favorite(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='favorites')
    flight = models.ForeignKey(Flight, on_delete=models.CASCADE, related_name='favorited_by')

    class Meta:
        verbose_name = 'შენახული ფრენა'
        verbose_name_plural = 'შენახული ფრენები'
        constraints = [models.UniqueConstraint(fields=['user', 'flight'], name='unique_favorite')]
