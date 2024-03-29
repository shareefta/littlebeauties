# Generated by Django 4.2.8 on 2024-01-03 04:49

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0006_accountuser_alter_profile_phone_number'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='accountuser',
            options={'verbose_name': 'user account', 'verbose_name_plural': 'user accounts'},
        ),
        migrations.AlterField(
            model_name='profile',
            name='uid',
            field=models.CharField(default='<function uuid4 at 0x0000024CC6E89670>', max_length=200),
        ),
        migrations.AlterField(
            model_name='profile',
            name='user',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='profile', to='accounts.accountuser'),
        ),
    ]
