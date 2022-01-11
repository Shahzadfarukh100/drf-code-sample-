# Generated by Django 2.2.4 on 2019-11-06 15:06

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import model_utils.fields
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('account', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='GeneralAbsence',
            fields=[
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('subject', models.CharField(max_length=256)),
                ('body', models.TextField(blank=True, null=True)),
                ('status', models.CharField(choices=[(1, 'PENDING'), (2, 'APPROVED'), (3, 'REJECTED')], default=1, max_length=20)),
                ('start_date', models.DateTimeField()),
                ('end_date', models.DateTimeField(blank=True, null=True)),
                ('deleted_at', models.DateTimeField(blank=True, null=True)),
                ('company', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='account.Company')),
                ('department', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, to='account.Department')),
                ('submitted_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='general_absences', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-start_date'],
            },
        ),
        migrations.CreateModel(
            name='EmployeeAbsenceType',
            fields=[
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=50)),
                ('description', models.TextField()),
                ('entitlement', models.SmallIntegerField(default=0, help_text='absences entitlement in hours')),
                ('period', models.CharField(choices=[(1, 'PER_WEEK'), (2, 'PER_MONTH'), (3, 'PER_YEAR'), (4, 'PER_EMPLOYMENT')], default=3, max_length=16)),
                ('submit_before_days', models.SmallIntegerField(default=0)),
                ('paid', models.BooleanField(default=False)),
                ('hourly', models.BooleanField(default=False)),
                ('deleted_at', models.DateTimeField(blank=True, null=True)),
                ('company', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='account.Company')),
            ],
            options={
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='EmployeeAbsence',
            fields=[
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('subject', models.CharField(max_length=256)),
                ('body', models.TextField(blank=True, null=True)),
                ('status', models.CharField(choices=[(1, 'PENDING'), (2, 'APPROVED'), (3, 'REJECTED')], default=1, max_length=20)),
                ('start_date', models.DateTimeField()),
                ('end_date', models.DateTimeField(blank=True, null=True)),
                ('duration', models.DurationField(blank=True, help_text='duration in hours', null=True)),
                ('submitted_on', models.DateTimeField()),
                ('remarks', models.TextField(blank=True, null=True)),
                ('absence_type', models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, to='absence.EmployeeAbsenceType')),
                ('company', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='account.Company')),
                ('department', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='account.Department')),
                ('submitted_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='absences', to=settings.AUTH_USER_MODEL)),
                ('submitted_to', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='approvals', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-start_date'],
            },
        ),
    ]