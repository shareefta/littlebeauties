# Generated by Django 4.2.8 on 2024-01-14 09:02

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0035_remove_userprofile_phone_number_alter_profile_uid'),
    ]

    operations = [
        migrations.AlterField(
            model_name='profile',
            name='uid',
            field=models.CharField(default='<function uuid4 at 0x000001C13F5B2C10>', max_length=200),
        ),
    ]