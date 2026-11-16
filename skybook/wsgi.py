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
    from django.core.management import call_command

    from flights.models import Flight

    call_command('migrate', interactive=False, verbosity=0)
    if not Flight.objects.exists():
        call_command('seed_flights', verbosity=0)

# Vercel-ის Python runtime ეძებს ცვლადს სახელით `app`
app = application
