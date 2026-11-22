from django.core.management.base import BaseCommand
from django.utils import timezone

from flights.models import Airline, City, Flight
from flights.seed import generate_flights


class Command(BaseCommand):
    help = 'ბაზას ავსებს ფრენებით: ყოველ მარშრუტზე ყოველდღე 1-2 ფრენა შემთხვევით დროს.'

    def add_arguments(self, parser):
        parser.add_argument('--days', type=int, default=60, help='რამდენი დღის ფრენები შეიქმნას')
        parser.add_argument('--max-per-route', type=int, default=2, help='მაქსიმუმ რამდენი ფრენა დღეში ერთ მარშრუტზე')

    def handle(self, *args, days, max_per_route, **options):
        # მომავალი ფრენები, რომლებზეც ჯავშანი არ არის, იშლება და თავიდან იქმნება
        Flight.objects.filter(bookings__isnull=True, return_bookings__isnull=True,
                              departure_time__gt=timezone.now()).delete()
        count = generate_flights(City, Airline, Flight, days=days, max_per_route=max_per_route)
        self.stdout.write(self.style.SUCCESS(f'შეიქმნა {count} ფრენა'))
