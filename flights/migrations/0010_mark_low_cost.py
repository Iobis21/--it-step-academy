"""ლოუქოსტერი ავიაკომპანიების მონიშვნა (Wizz Air, Pegasus)."""
from django.db import migrations


def mark(apps, schema_editor):
    from flights.seed import LOW_COST

    Airline = apps.get_model('flights', 'Airline')
    Airline.objects.filter(code__in=LOW_COST).update(low_cost=True)


class Migration(migrations.Migration):
    dependencies = [('flights', '0009_baggage')]

    operations = [migrations.RunPython(mark, migrations.RunPython.noop)]
