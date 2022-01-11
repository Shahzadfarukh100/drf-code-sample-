# Generated by Django 2.2.4 on 2019-12-24 12:22

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('absence', '0006_merge_20191223_0830'),
    ]

    operations = [
        migrations.AddField(
            model_name='employeeabsence',
            name='submitted_for',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='absences', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='employeeabsence',
            name='submitted_by',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='submitted', to=settings.AUTH_USER_MODEL),
        ),
    ]
