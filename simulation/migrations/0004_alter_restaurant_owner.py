# Generated manually to handle NULL owner values

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def delete_restaurants_with_null_owner(apps, schema_editor):
    """Delete restaurants that have NULL owners since they're orphaned."""
    Restaurant = apps.get_model('simulation', 'Restaurant')
    Restaurant.objects.filter(owner__isnull=True).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('simulation', '0003_alter_simulationresult_restaurant'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # First, delete any restaurants with NULL owners
        migrations.RunPython(delete_restaurants_with_null_owner, migrations.RunPython.noop),
        # Then, alter the field to be non-nullable
        migrations.AlterField(
            model_name='restaurant',
            name='owner',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='owned_restaurants',
                to=settings.AUTH_USER_MODEL,
                null=False,
                blank=False,
            ),
        ),
    ]

