# Generated by Django 2.2.4 on 2019-12-23 10:49

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('account', '0004_remove_companyemployeesettings_overwrite_the_cannot_preference'),
        ('absence', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='generalabsence',
            name='department',
        ),
        migrations.AddField(
            model_name='generalabsence',
            name='department',
            field=models.ManyToManyField(to='account.Department'),
        ),
    ]
