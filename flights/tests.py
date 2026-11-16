from datetime import timedelta

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
            'first_name': 'გიო', 'last_name': 'ტესტი', 'personal_id': '01001012345',
            'phone': '599123456', 'email': 'a@a.ge',
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

    def _make_return(self):
        f = self.flight
        return Flight.objects.create(
            flight_number='RT100', airline=f.airline, origin=f.destination, destination=f.origin,
            departure_time=f.arrival_time + timedelta(days=3),
            arrival_time=f.arrival_time + timedelta(days=3, hours=2),
            economy_price=200, business_price=600,
        )

    def test_return_search_and_detail_pages(self):
        ret = self._make_return()
        d = ret.departure_time.date().isoformat()
        r = self.client.get('/search/', {'trip_type': 'return', 'return_date': d})
        self.assertContains(r, f'?return_date={d}')
        r = self.client.get(f'/flights/{self.flight.pk}/', {'return_date': d})
        self.assertContains(r, f'?return={ret.pk}')
        r = self.client.get(f'/flights/{self.flight.pk}/', {'return': ret.pk})
        self.assertContains(r, 'data-leg="ret"')

    def test_return_requires_return_date(self):
        r = self.client.get('/search/', {'trip_type': 'return'})
        self.assertContains(r, 'მიუთითე დაბრუნების თარიღი')

    def test_round_trip_booking(self):
        ret = self._make_return()
        self.login()
        data = {'seat': ['3A', '3B'], 'return_seat': ['7C', '7D'], 'return_flight': ret.pk}
        for s in ['3A', '3B']:
            data.update({f'first_name_{s}': 'ა', f'last_name_{s}': 'ბ', f'passport_{s}': '01001'})
        self.client.post(reverse('book', args=[self.flight.pk]), data)
        b = Booking.objects.get()
        self.assertEqual(b.return_flight, ret)
        self.assertEqual(b.total_price, self.flight.economy_price * 2 + ret.economy_price * 2)
        self.assertEqual({'7C', '7D'}, ret.taken_seats())
        self.assertEqual(self.client.get(reverse('profile')).status_code, 200)

    def test_round_trip_seat_count_must_match(self):
        ret = self._make_return()
        self.login()
        data = {'seat': ['3A', '3B'], 'return_seat': ['7C'], 'return_flight': ret.pk}
        for s in ['3A', '3B']:
            data.update({f'first_name_{s}': 'ა', f'last_name_{s}': 'ბ', f'passport_{s}': '01001'})
        self.client.post(reverse('book', args=[self.flight.pk]), data)
        self.assertEqual(Booking.objects.count(), 0)

    def test_register_requires_valid_personal_id(self):
        r = self.client.post(reverse('register'), {
            'first_name': 'გიო', 'last_name': 'ტესტი', 'personal_id': '123',
            'phone': '599123456', 'email': 'b@b.ge',
            'password1': 'Skybook!2026', 'password2': 'Skybook!2026',
        })
        self.assertEqual(r.status_code, 200)
        self.assertFalse(User.objects.filter(email='b@b.ge').exists())

    def test_ticket_after_booking_and_checkin(self):
        self.login()
        r = self.book(['3A'])
        b = Booking.objects.get()
        self.assertEqual(len(b.pnr), 6)
        self.assertRedirects(r, reverse('ticket', args=[b.pnr]))
        self.assertContains(self.client.get(reverse('ticket', args=[b.pnr])), b.pnr)
        self.client.post(reverse('do_checkin', args=[b.pnr]))
        self.assertTrue(b.passengers.get().checked_in)

    def test_ticket_hidden_from_strangers(self):
        self.login()
        self.book(['3A'])
        b = Booking.objects.get()
        self.client.logout()
        r = self.client.get(reverse('ticket', args=[b.pnr]))
        self.assertRedirects(r, reverse('checkin'))
        # კოდით + გვარით ხელმისაწვდომია
        r = self.client.post(reverse('checkin'), {'pnr': b.pnr.lower(), 'last_name': 'ბ'})
        self.assertRedirects(r, reverse('ticket', args=[b.pnr]))

    def test_cannot_cancel_others_booking(self):
        self.login()
        self.book(['4C'])
        b = Booking.objects.get()
        self.client.logout()
        self.login(email='x@x.ge', phone='599000000')
        r = self.client.post(reverse('cancel_booking', args=[b.pk]))
        self.assertEqual(r.status_code, 404)
