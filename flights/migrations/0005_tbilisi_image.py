"""თბილისის სურათი — მშვიდობის ხიდი (static/img)."""
from django.db import migrations


def update_images(apps, schema_editor):
    from flights.seed import CITIES

    City = apps.get_model('flights', 'City')
    for _, code, image, _, _ in CITIES:
        City.objects.filter(airport_code=code).update(image_url=image)


class Migration(migrations.Migration):
    dependencies = [('flights', '0004_local_city_images')]

    operations = [migrations.RunPython(update_images, migrations.RunPython.noop)]
