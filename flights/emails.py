"""ბილეთის გაგზავნა ელ-ფოსტაზე."""
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string


def send_ticket_email(request, booking):
    """გადახდის შემდეგ ბილეთს ვაგზავნით საკონტაქტო ელ-ფოსტაზე.

    აბრუნებს True-ს თუ გაიგზავნა, False-ს თუ ვერ გაიგზავნა.
    """
    if not booking.contact_email:
        return False

    legs = [(booking.flight, booking.outbound_passengers())]
    if booking.return_flight:
        legs.append((booking.return_flight, booking.return_passengers()))

    context = {
        'booking': booking,
        'legs': legs,
        'ticket_url': request.build_absolute_uri(f'/ticket/{booking.pnr}/'),
        'checkin_url': request.build_absolute_uri('/checkin/'),
    }
    subject = f'SkyBook — თქვენი ბილეთი {booking.pnr}'
    text = render_to_string('emails/ticket.txt', context)
    html = render_to_string('emails/ticket.html', context)

    message = EmailMultiAlternatives(subject, text, settings.DEFAULT_FROM_EMAIL, [booking.contact_email])
    message.attach_alternative(html, 'text/html')
    try:
        message.send()
        return True
    except Exception as error:  # SMTP სერვერის შეცდომა — ბილეთი მაინც შეძენილია
        print('ელ-ფოსტა ვერ გაიგზავნა:', error)
        return False
