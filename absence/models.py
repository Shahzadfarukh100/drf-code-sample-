import datetime as dt
import uuid
from datetime import timedelta

from django.db import models
from django.db.models import Q, Case, When
from django.utils.translation import ugettext_lazy as _
from model_utils.models import TimeStampedModel

from absence.manager import EmployeeAbsencesTypeManager
from account.models import Employee
from constants.db import ABSENCE_ENTITLEMENT_PERIOD_CHOICE, ABSENCE_STATUS_CHOICES, DURATION
from history.connector import connect


class EmployeeAbsenceType(TimeStampedModel):
    objects = EmployeeAbsencesTypeManager()

    id = models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True)
    name = models.CharField(max_length=50)
    description = models.TextField(max_length=500)
    entitlement = models.PositiveSmallIntegerField(default=0, help_text='absences entitlement in hours')
    period = models.PositiveSmallIntegerField(default=ABSENCE_ENTITLEMENT_PERIOD_CHOICE.PER_YEAR,
                                      choices=ABSENCE_ENTITLEMENT_PERIOD_CHOICE)
    submit_before_days = models.PositiveSmallIntegerField(default=0)
    paid = models.BooleanField(default=False)
    duration = models.PositiveSmallIntegerField(default=DURATION.FULL_DAY,
                                                choices=DURATION)
    company = models.ForeignKey('account.Company', on_delete=models.CASCADE, db_index=True)
    deleted_at = models.DateTimeField(null=True, default=None)

    def __str__(self):
        return self.name

    @property
    def hourly(self):
        return self.duration == DURATION.HOURLY

    class Meta:
        ordering = ['name']


@connect()
class EmployeeAbsence(TimeStampedModel):

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    subject = models.CharField(max_length=256)
    submitted_for = models.ForeignKey('account.Employee', on_delete=models.CASCADE, related_name='submitted_for')
    submitted_by = models.ForeignKey('account.Employee', on_delete=models.CASCADE, related_name='submitted_by')
    submitted_to = models.ForeignKey(
        'account.Employee', on_delete=models.CASCADE, related_name='submitted_to', null=True, blank=True,
    )
    status = models.PositiveSmallIntegerField(choices=ABSENCE_STATUS_CHOICES, default=ABSENCE_STATUS_CHOICES.PENDING)
    start = models.DateTimeField()
    end = models.DateTimeField(null=True, blank=True)
    company = models.ForeignKey('account.Company', on_delete=models.CASCADE, db_index=True)
    absence_type = models.ForeignKey(EmployeeAbsenceType, on_delete=models.DO_NOTHING)

    class Meta:
        ordering = ['-start']

    @classmethod
    def get_event_queryset(cls, **kwargs):
        qs = cls.objects.filter(**kwargs)
        qs = qs.annotate(
            title=models.Value(str(_('ABSENT')), output_field=models.CharField()),
            background_color=models.Value('#E57373', output_field=models.CharField()),
            type=models.Value('ABSENCE', output_field=models.CharField()),
            allDay=Case(
                When(absence_type__duration = DURATION.HOURLY, then=False),
                default=True,
                output_field=models.BooleanField()
            )
        )
        qs = qs.only('id', 'start', 'end')
        return qs

    def get_comments(self):
        return self.employeeabsencecomment_set.all()

    def is_hourly(self):
        return self.absence_type.hourly

    def is_created_for_past(self):
        return self.created > self.start

    def get_end(self):
        if not self.is_hourly():
            return self.end - timedelta(days=1)
        return self.end


class EmployeeAbsenceComment(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    absence = models.ForeignKey(EmployeeAbsence, on_delete=models.CASCADE)
    comment = models.TextField(null=True, blank=True, max_length=500)
    # the latest status of the leave when users commented on the leave
    status = models.CharField(max_length=20, choices=ABSENCE_STATUS_CHOICES)
    commented_by = models.ForeignKey(Employee, on_delete=models.CASCADE)

    class Meta:
        ordering = ['-created']


class GeneralAbsence(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    subject = models.CharField(max_length=256)
    body = models.TextField(null=True, blank=True, max_length=500)
    status = models.PositiveSmallIntegerField(choices=ABSENCE_STATUS_CHOICES, default=ABSENCE_STATUS_CHOICES.PENDING)
    submitted_by = models.ForeignKey('account.Employee', on_delete=models.CASCADE,
                                     related_name='general_absences')
    start = models.DateTimeField()
    end = models.DateTimeField()

    deleted_at = models.DateTimeField(null=True, blank=True)
    department = models.ManyToManyField('account.Department', related_name='general_absence_department')
    company = models.ForeignKey('account.Company', on_delete=models.CASCADE, db_index=True)

    class Meta:
        ordering = ['-start']


    @classmethod
    def get_event_queryset(cls, *args, **kwargs):
        qs = cls.objects.filter(*args, **kwargs)
        qs = qs.annotate(
            title=models.Value(str(_('ABSENT')), output_field=models.CharField()),
            background_color=models.Value('#E57373', output_field=models.CharField()),
            type=models.Value('GENERAL_ABSENCE', output_field=models.CharField()),
            allDay=models.Value(True, output_field=models.BooleanField()),
        )
        qs = qs.only('id', 'start', 'end')
        return qs

    @classmethod
    def for_employee(cls, employee):
        q = Q(department__isnull=True, company=employee.company)
        q = q | Q(department__isnull=False, department__in=[employee.department])
        return cls.objects.filter(q)

    def get_end(self):
        return self.end - dt.timedelta(days=1)