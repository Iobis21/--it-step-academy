"""ძველი სატესტო ფრენების ჩანაცვლება რეალისტური ფასებით და მარშრუტებით."""
from django.db import migrations
from django.utils import timezone


def regenerate(apps, schema_editor):
    from flights.seed import generate_flights

    City = apps.get_model('flights', 'City')
    Airline = apps.get_model('flights', 'Airline')
    Flight = apps.get_model('flights', 'Flight')
    if not Flight.objects.exists():
        return  # ცარიელ ბაზას seed_flights შეავსებს
    Flight.objects.filter(bookings__isnull=True, departure_time__gt=timezone.now()).delete()
    generate_flights(City, Airline, Flight)


class Migration(migrations.Migration):
    dependencies = [('flights', '0001_initial')]

    operations = [migrations.RunPython(regenerate, migrations.RunPython.noop)]
