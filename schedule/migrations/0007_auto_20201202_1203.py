# Generated by Django 2.2.4 on 2020-12-02 12:03

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('schedule', '0006_auto_20200716_0344'),
    ]

    operations = [
        migrations.AlterField(
            model_name='schedule',
            name='comment',
            field=models.TextField(blank=True, max_length=500, null=True),
        ),
        migrations.AlterField(
            model_name='schedulefeedback',
            name='comment',
            field=models.TextField(blank=True, max_length=5000, null=True),
        ),
    ]
