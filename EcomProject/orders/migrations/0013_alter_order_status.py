# Generated by Django 4.2.8 on 2024-01-26 06:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0012_order_is_cancelled'),
    ]

    operations = [
        migrations.AlterField(
            model_name='order',
            name='status',
            field=models.CharField(choices=[('New', 'New'), ('Pending', 'Pending'), ('Accepted', 'Accepted'), ('Cancelled', 'Cancelled'), ('Delivered', 'Delivered'), ('Returned', 'Returned'), ('Completed', 'Completed')], default='New', max_length=10),
        ),
    ]
