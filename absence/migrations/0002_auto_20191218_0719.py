# Generated by Django 2.2.4 on 2019-12-18 07:19

import datetime
from django.db import migrations, models
from django.utils.timezone import utc


class Migration(migrations.Migration):

    dependencies = [
        ('absence', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='generalabsence',
            name='end_date',
            field=models.DateTimeField(default=datetime.datetime(2019, 12, 18, 7, 19, 29, 72981, tzinfo=utc)),
            preserve_default=False,
        ),
    ]
