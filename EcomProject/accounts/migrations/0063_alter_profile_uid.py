# Generated by Django 4.2.8 on 2024-02-03 02:30

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0062_alter_profile_uid'),
    ]

    operations = [
        migrations.AlterField(
            model_name='profile',
            name='uid',
            field=models.CharField(default='<function uuid4 at 0x000001CCB9312C10>', max_length=200),
        ),
    ]
