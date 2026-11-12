from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from .models import Booking, Flight


class BookingFlowTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('seed_flights', days=3, per_day=4, verbosity=0)
        cls.flight = Flight.objects.first()

    def login(self, email='t@t.ge', phone='599123456'):
        user = User.objects.create_user(username=email, email=email, phone=phone, password='Skybook!2026',
                                        first_name='გიო', last_name='ტესტი')
        self.client.force_login(user)
        return user

    def book(self, seats):
        data = {'seat': seats}
        for s in seats:
            data.update({f'first_name_{s}': 'ა', f'last_name_{s}': 'ბ', f'passport_{s}': '01001'})
        return self.client.post(reverse('book', args=[self.flight.pk]), data)

    def test_public_pages(self):
        for url in ['/', '/search/', f'/search/?origin={self.flight.origin_id}',
                    f'/flights/{self.flight.pk}/', '/accounts/login/', '/accounts/register/']:
            self.assertEqual(self.client.get(url).status_code, 200, url)

    def test_register_and_login(self):
        r = self.client.post(reverse('register'), {
            'first_name': 'გიო', 'last_name': 'ტესტი', 'phone': '599123456', 'email': 'a@a.ge',
            'password1': 'Skybook!2026', 'password2': 'Skybook!2026',
        })
        self.assertRedirects(r, reverse('home'))
        self.client.logout()
        r = self.client.post(reverse('login'), {'email': 'a@a.ge', 'password': 'Skybook!2026'})
        self.assertRedirects(r, reverse('home'))

    def test_booking_requires_login(self):
        r = self.book(['3A'])
        self.assertEqual(r.status_code, 302)
        self.assertIn(reverse('login'), r['Location'])
        self.assertEqual(Booking.objects.count(), 0)

    def test_book_and_price(self):
        self.login()
        self.book(['3A', '3B'])
        b = Booking.objects.get()
        self.assertEqual(b.total_price, self.flight.economy_price * 2)
        self.assertEqual(b.cabin, 'economy')
        self.assertEqual(self.client.get(reverse('profile')).status_code, 200)

    def test_seat_cannot_be_double_booked(self):
        self.login()
        self.book(['3A'])
        self.book(['3A'])
        self.assertEqual(Booking.objects.count(), 1)

    def test_mixed_cabins_rejected(self):
        self.login()
        self.book(['1A', '5A'])
        self.assertEqual(Booking.objects.count(), 0)

    def test_cancel_frees_seat(self):
        self.login()
        self.book(['4C'])
        b = Booking.objects.get()
        self.client.post(reverse('cancel_booking', args=[b.pk]))
        self.assertNotIn('4C', self.flight.taken_seats())

    def test_cannot_cancel_others_booking(self):
        self.login()
        self.book(['4C'])
        b = Booking.objects.get()
        self.client.logout()
        self.login(email='x@x.ge', phone='599000000')
        r = self.client.post(reverse('cancel_booking', args=[b.pk]))
        self.assertEqual(r.status_code, 404)
