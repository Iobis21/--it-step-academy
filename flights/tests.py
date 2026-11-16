from datetime import timedelta

from django.core import mail
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

    def test_guest_booking_requires_email(self):
        # სტუმარი ელ-ფოსტის გარეშე ვერ დაჯავშნის
        self.book(['5A'])
        self.client.post(reverse('book', args=[self.flight.pk]), {
            'seat': ['5A'], 'first_name_5A': 'ა', 'last_name_5A': 'ბ', 'passport_5A': '1',
            'contact_email': 'not-an-email',
        })
        self.assertEqual(Booking.objects.count(), 0)

    def test_guest_booking_and_ticket_email(self):
        r = self.client.post(reverse('book', args=[self.flight.pk]), {
            'seat': ['5A'], 'first_name_5A': 'ანა', 'last_name_5A': 'ბერიძე', 'passport_5A': '1',
            'contact_email': 'guest@mail.ge', 'contact_phone': '599111222',
        })
        b = Booking.objects.get()
        self.assertIsNone(b.user)
        self.assertEqual(b.contact_email, 'guest@mail.ge')
        self.assertRedirects(r, reverse('pay', args=[b.pnr]))

        self.assertEqual(len(mail.outbox), 0)  # გადახდამდე წერილი არ იგზავნება
        self.pay(b)
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertEqual(email.to, ['guest@mail.ge'])
        self.assertIn(b.pnr, email.subject)
        self.assertIn('ბერიძე'.upper(), email.body)
        self.assertIn(f'/ticket/{b.pnr}/', email.body)
        # სტუმარი ბილეთს იმავე სესიაში ხედავს
        self.assertContains(self.client.get(reverse('ticket', args=[b.pnr])), b.pnr)

    def test_logged_in_user_email_used(self):
        user = self.login()
        self.book(['5A'])
        b = Booking.objects.get()
        self.assertEqual((b.user, b.contact_email), (user, user.email))
        self.pay(b)
        self.assertEqual(mail.outbox[0].to, [user.email])

    def test_book_and_price(self):
        self.login()
        self.book(['5A', '5B'])
        b = Booking.objects.get()
        self.assertEqual(b.total_price, self.flight.economy_price * 2)
        self.assertEqual(b.cabin, 'economy')
        self.assertEqual(self.client.get(reverse('profile')).status_code, 200)

    def test_seat_cannot_be_double_booked(self):
        self.login()
        self.book(['5A'])
        self.book(['5A'])
        self.assertEqual(Booking.objects.count(), 1)

    def test_mixed_cabins_rejected(self):
        self.login()
        self.book(['1A', '6A'])
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
        self.assertContains(r, f'return_date={d}')
        r = self.client.get(f'/flights/{self.flight.pk}/', {'return_date': d})
        self.assertContains(r, f'return={ret.pk}')
        r = self.client.get(f'/flights/{self.flight.pk}/', {'return': ret.pk})
        self.assertContains(r, 'data-leg="ret"')

    def test_return_requires_return_date(self):
        r = self.client.get('/search/', {'trip_type': 'return'})
        self.assertContains(r, 'მიუთითე დაბრუნების თარიღი')

    def test_round_trip_booking(self):
        ret = self._make_return()
        self.login()
        data = {'seat': ['5A', '5B'], 'return_seat': ['7C', '7D'], 'return_flight': ret.pk}
        for s in ['5A', '5B']:
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
        data = {'seat': ['5A', '5B'], 'return_seat': ['7C'], 'return_flight': ret.pk}
        for s in ['5A', '5B']:
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

    CARD = {'card_name': 'GIO TESTI', 'card_number': '4242 4242 4242 4242', 'expiry': '12/39', 'cvv': '123'}

    def pay(self, booking, **override):
        return self.client.post(reverse('pay', args=[booking.pnr]), {**self.CARD, **override})

    def test_ticket_after_booking_payment_and_checkin(self):
        self.login()
        r = self.book(['5A'])
        b = Booking.objects.get()
        self.assertEqual(len(b.pnr), 6)
        self.assertEqual(b.status, 'pending')
        self.assertRedirects(r, reverse('pay', args=[b.pnr]))
        # გადახდამდე ბილეთი არ ჩანს — გადახდაზე გადაგვიყვანს
        self.assertRedirects(self.client.get(reverse('ticket', args=[b.pnr])), reverse('pay', args=[b.pnr]))
        r = self.pay(b)
        self.assertRedirects(r, reverse('ticket', args=[b.pnr]))
        b.refresh_from_db()
        self.assertEqual((b.status, b.card_last4), ('active', '4242'))
        self.assertContains(self.client.get(reverse('ticket', args=[b.pnr])), b.pnr)
        self.client.post(reverse('do_checkin', args=[b.pnr]))
        self.assertTrue(b.passengers.get().checked_in)

    def test_invalid_card_rejected(self):
        self.login()
        self.book(['5A'])
        b = Booking.objects.get()
        r = self.pay(b, card_number='4242 4242 4242 4241')
        self.assertContains(r, 'ბარათის ნომერი არასწორია')
        r = self.pay(b, expiry='01/20')
        self.assertContains(r, 'ვადა გაუვიდა')
        b.refresh_from_db()
        self.assertEqual(b.status, 'pending')

    def test_unpaid_booking_expires_and_frees_seats(self):
        self.login()
        self.book(['5A'])
        b = Booking.objects.get()
        self.assertIn('5A', self.flight.taken_seats())
        Booking.objects.filter(pk=b.pk).update(created_at=b.created_at - timedelta(minutes=16))
        self.assertNotIn('5A', self.flight.taken_seats())
        self.client.get(reverse('pay', args=[b.pnr]))
        b.refresh_from_db()
        self.assertEqual(b.status, 'cancelled')

    def test_return_ticket_by_number(self):
        self.login()
        self.book(['5A'])
        b = Booking.objects.get()
        self.pay(b)
        self.client.logout()
        self.client.post(reverse('checkin'), {'pnr': b.pnr, 'last_name': 'ბ'})
        self.client.post(reverse('cancel_ticket', args=[b.pnr]))
        b.refresh_from_db()
        self.assertEqual(b.status, 'cancelled')
        self.assertNotIn('5A', self.flight.taken_seats())

    def test_ticket_hidden_from_strangers(self):
        self.login()
        self.book(['5A'])
        b = Booking.objects.get()
        self.pay(b)
        self.client.logout()
        r = self.client.get(reverse('ticket', args=[b.pnr]))
        self.assertRedirects(r, reverse('checkin'))
        # კოდით + გვარით ხელმისაწვდომია
        r = self.client.post(reverse('checkin'), {'pnr': b.pnr.lower(), 'last_name': 'ბ'})
        self.assertRedirects(r, reverse('ticket', args=[b.pnr]))

    def test_business_booking_and_invalid_seat(self):
        self.login()
        self.book(['1B'])  # ბიზნესში B ადგილი არ არსებობს (2+2: A C | D F)
        self.assertEqual(Booking.objects.count(), 0)
        self.book(['1A', '1C'])
        b = Booking.objects.get()
        self.assertEqual(b.cabin, 'business')
        self.assertEqual(b.total_price, self.flight.business_price * 2)

    def test_detail_page_shows_plane(self):
        r = self.client.get(f'/flights/{self.flight.pk}/', {'cabin': 'business'})
        self.assertContains(r, 'class="plane"')
        self.assertContains(r, 'value="business" checked')

    def _flight_of(self, low_cost):
        return Flight.objects.filter(airline__low_cost=low_cost).first()

    def _book_with_bags(self, flight, seat, cabin_bag, checked):
        return self.client.post(reverse('book', args=[flight.pk]), {
            'seat': [seat], f'first_name_{seat}': 'ა', f'last_name_{seat}': 'ბ', f'passport_{seat}': '1',
            f'cabin_bag_{seat}': '1' if cabin_bag else '', f'checked_{seat}': str(checked),
        })

    def test_low_cost_baggage_extras(self):
        f = self._flight_of(True)
        self.login()
        self._book_with_bags(f, '5A', True, 2)
        b = Booking.objects.get()
        self.assertEqual(b.baggage_price, 49 + 2 * 99)
        self.assertEqual(b.total_price, f.economy_price + 49 + 2 * 99)
        p = b.passengers.get()
        self.assertTrue(p.extra_cabin_bag)
        self.assertIn('ჩემოდანი 2 × 20 კგ', p.baggage_lines())

    def test_full_service_includes_cabin_bag(self):
        f = self._flight_of(False)
        self.login()
        self._book_with_bags(f, '5A', True, 1)  # ხელბარგი უკვე შედის — უფასოა
        b = Booking.objects.get()
        self.assertEqual(b.baggage_price, 129)
        self.assertFalse(b.passengers.get().extra_cabin_bag)
        self.assertIn('ჩემოდანი 2 × 23 კგ', b.passengers.get().baggage_lines())

    def test_too_many_extra_bags_rejected(self):
        self.login()
        self._book_with_bags(self.flight, '5A', False, 9)
        self.assertEqual(Booking.objects.count(), 0)

    # ===== API =====
    def test_api_lists(self):
        self.assertEqual(self.client.get('/api/').status_code, 200)
        self.assertEqual(len(self.client.get('/api/cities/').json()), 10)
        self.assertTrue(self.client.get('/api/airlines/').json())

    def test_api_flight_search_and_detail(self):
        f = self.flight
        data = self.client.get('/api/flights/', {'from': f.origin.airport_code.lower(),
                                                 'date': f.departure_time.date().isoformat()}).json()
        self.assertIn(f.id, [x['id'] for x in data['results']])
        self.assertTrue(all(x['from']['code'] == f.origin.airport_code for x in data['results']))
        self.assertEqual(self.client.get('/api/flights/', {'date': 'bad'}).status_code, 400)
        d = self.client.get(f'/api/flights/{f.id}/').json()
        self.assertEqual(d['seats']['total'], 84)
        self.assertIn('economy', d['baggage'])
        self.assertEqual(self.client.get('/api/flights/999999/').status_code, 404)

    def test_api_ticket(self):
        self.login()
        self.book(['5A'])
        b = Booking.objects.get()
        self.assertEqual(self.client.get(f'/api/tickets/{b.pnr}/').status_code, 400)
        self.assertEqual(self.client.get(f'/api/tickets/{b.pnr}/', {'last_name': 'სხვა'}).status_code, 404)
        d = self.client.get(f'/api/tickets/{b.pnr.lower()}/', {'last_name': 'ბ'}).json()
        self.assertEqual(d['ticket_number'], b.pnr)
        self.assertEqual(d['legs'][0]['passengers'][0]['seat'], '5A')
        self.assertNotIn('passport', str(d))
        self.assertIn('5A', self.client.get(f'/api/flights/{self.flight.id}/').json()['seats']['taken'])

    def test_cannot_cancel_others_booking(self):
        self.login()
        self.book(['4C'])
        b = Booking.objects.get()
        self.client.logout()
        self.login(email='x@x.ge', phone='599000000')
        r = self.client.post(reverse('cancel_booking', args=[b.pk]))
        self.assertEqual(r.status_code, 404)
