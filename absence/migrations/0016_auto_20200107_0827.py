# Generated by Django 2.2.4 on 2020-01-07 08:27

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('absence', '0015_auto_20200106_0855'),
    ]

    operations = [
        migrations.AlterField(
            model_name='employeeabsence',
            name='submitted_to',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='submitted_to', to=settings.AUTH_USER_MODEL),
        ),
    ]
