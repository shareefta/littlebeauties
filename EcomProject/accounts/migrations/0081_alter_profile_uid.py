# Generated by Django 4.2.8 on 2024-02-14 07:18

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0080_remove_profile_phone_number_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='profile',
            name='uid',
            field=models.CharField(default='<function uuid4 at 0x000002BA5BC62C10>', max_length=200),
        ),
    ]
