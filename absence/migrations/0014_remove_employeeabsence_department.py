# Generated by Django 2.2.4 on 2020-01-06 08:43

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('absence', '0013_auto_20200105_1426'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='employeeabsence',
            name='department',
        ),
    ]