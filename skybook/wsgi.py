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

    # ადმინის ანგარიში Vercel-ის გარემოს ცვლადებიდან (ADMIN_EMAIL, ADMIN_PASSWORD, ADMIN_PHONE).
    # თუ ამ ელ-ფოსტით მომხმარებელი უკვე არსებობს — მას ადმინის უფლებებს ვაძლევთ.
    from accounts.models import User

    # strip() — ზედმეტი სივრცეების/ხაზის ბოლოს მოსაშორებლად
    admin_email = os.environ.get('ADMIN_EMAIL', '').strip().lower()
    admin_password = os.environ.get('ADMIN_PASSWORD', '').strip()
    if admin_email and admin_password:
        admin = User.objects.filter(email=admin_email).first()
        if admin is None:
            User.objects.create_superuser(
                username=admin_email, email=admin_email, password=admin_password,
                phone=os.environ.get('ADMIN_PHONE', '500000000'), first_name='ადმინი',
            )
        elif not admin.is_superuser or not admin.check_password(admin_password):
            admin.is_staff = True
            admin.is_superuser = True
            admin.set_password(admin_password)
            admin.save()

# Vercel-ის Python runtime ეძებს ცვლადს სახელით `app`
app = application
