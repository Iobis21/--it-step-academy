"""არსებულ ჯავშნებს ჯავშნის კოდის (PNR) მინიჭება."""
from django.db import migrations


def fill_pnr(apps, schema_editor):
    from flights.models import generate_pnr

    Booking = apps.get_model('flights', 'Booking')
    for booking in Booking.objects.filter(pnr__isnull=True):
        booking.pnr = generate_pnr(Booking)
        booking.save(update_fields=['pnr'])


class Migration(migrations.Migration):
    dependencies = [('flights', '0007_pnr_and_checkin')]

    operations = [migrations.RunPython(fill_pnr, migrations.RunPython.noop)]
