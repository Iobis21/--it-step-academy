from django.core.management.base import BaseCommand
from django.utils import timezone

from flights.models import Airline, City, Flight
from flights.seed import generate_flights


class Command(BaseCommand):
    help = 'ბაზას ავსებს სატესტო ფრენებით (რეალისტური ფასებით). მომავალი ფრენები ჯავშნების გარეშე იშლება და თავიდან იქმნება.'

    def add_arguments(self, parser):
        parser.add_argument('--days', type=int, default=30, help='რამდენი დღის ფრენები შეიქმნას')
        parser.add_argument('--per-day', type=int, default=8, help='ფრენების რაოდენობა დღეში')

    def handle(self, *args, days, per_day, **options):
        Flight.objects.filter(bookings__isnull=True, departure_time__gt=timezone.now()).delete()
        count = generate_flights(City, Airline, Flight, days=days, per_day=per_day)
        self.stdout.write(self.style.SUCCESS(f'შეიქმნა {count} ფრენა'))
