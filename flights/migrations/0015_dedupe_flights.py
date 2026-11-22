"""დუბლიკატი ფრენების გასწორება: ფრენები თავიდან, ბლოკით (ერთდროულად მხოლოდ ერთი)."""
from django.db import migrations


def regenerate(apps, schema_editor):
    from flights.seed import regenerate_future_flights

    Flight = apps.get_model('flights', 'Flight')
    if not Flight.objects.exists():
        return
    regenerate_future_flights(apps.get_model('flights', 'City'), apps.get_model('flights', 'Airline'), Flight)


class Migration(migrations.Migration):
    dependencies = [('flights', '0014_flights_every_day')]

    operations = [migrations.RunPython(regenerate, migrations.RunPython.noop)]
