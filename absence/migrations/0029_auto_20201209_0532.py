# Generated by Django 2.2.4 on 2020-12-09 05:32

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('absence', '0028_auto_20201202_1203'),
    ]

    operations = [
        migrations.AlterField(
            model_name='employeeabsence',
            name='status',
            field=models.PositiveSmallIntegerField(choices=[(1, 'PENDING'), (2, 'APPROVED'), (3, 'REJECTED'), (4, 'IN_REVIEW')], default=1),
        ),
        migrations.AlterField(
            model_name='employeeabsencetype',
            name='duration',
            field=models.PositiveSmallIntegerField(choices=[(1, 'FULL_DAY'), (2, 'HOURLY'), (3, 'QUITTING')], default=1),
        ),
        migrations.AlterField(
            model_name='employeeabsencetype',
            name='entitlement',
            field=models.PositiveSmallIntegerField(default=0, help_text='absences entitlement in hours'),
        ),
        migrations.AlterField(
            model_name='employeeabsencetype',
            name='period',
            field=models.PositiveSmallIntegerField(choices=[(1, 'PER_WEEK'), (2, 'PER_MONTH'), (3, 'PER_YEAR')], default=3),
        ),
        migrations.AlterField(
            model_name='generalabsence',
            name='status',
            field=models.PositiveSmallIntegerField(choices=[(1, 'PENDING'), (2, 'APPROVED'), (3, 'REJECTED'), (4, 'IN_REVIEW')], default=1),
        ),
    ]
