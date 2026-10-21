from django.db import migrations


class Migration(migrations.Migration):
    """Couriers become one role of the staff registry (keeps existing rows and order links)."""

    dependencies = [
        ('delivery', '0004_courier'),
        ('orders', '0004_order_courier'),
    ]

    operations = [
        migrations.RenameModel('Courier', 'Employee'),
    ]
