"""
WSGI config for skybook project.

It exposes the WSGI callable as a module-level variable named ``application``.
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'skybook.settings')

application = get_wsgi_application()

# Vercel-ზე: გაშვებისას ბაზის ცხრილები განახლდება და, თუ ცარიელია, ფრენებით შეივსება
if os.environ.get('VERCEL'):
    from datetime import timedelta

    from django.core.management import call_command
    from django.utils import timezone

    from flights.models import Flight

    call_command('migrate', interactive=False, verbosity=0)
    # ფრენები ყოველთვის იყოს მინიმუმ 2 კვირით წინ — თორემ თავიდან შეიქმნება
    if not Flight.objects.filter(departure_time__gt=timezone.now() + timedelta(days=14)).exists():
        call_command('seed_flights', verbosity=0)

# Vercel-ის Python runtime ეძებს ცვლადს სახელით `app`
app = application
