# Generated by Django 4.2.8 on 2024-02-06 12:19

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0074_account_phone_number_alter_profile_uid'),
    ]

    operations = [
        migrations.AlterField(
            model_name='profile',
            name='uid',
            field=models.CharField(default='<function uuid4 at 0x0000023F6F552C10>', max_length=200),
        ),
    ]
