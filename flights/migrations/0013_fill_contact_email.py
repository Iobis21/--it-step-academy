"""ძველ ჯავშნებს საკონტაქტო ელ-ფოსტად ვუწერთ მომხმარებლის ელ-ფოსტას."""
from django.db import migrations


def fill(apps, schema_editor):
    Booking = apps.get_model('flights', 'Booking')
    for booking in Booking.objects.filter(contact_email='').exclude(user=None):
        booking.contact_email = booking.user.email
        booking.contact_phone = booking.user.phone
        booking.save()


class Migration(migrations.Migration):
    dependencies = [('flights', '0012_guest_checkout')]

    operations = [migrations.RunPython(fill, migrations.RunPython.noop)]
