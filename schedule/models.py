import uuid

from django.contrib.postgres.fields import JSONField
from django.db import models
from model_utils.models import TimeStampedModel

from account.models import Employee
from constants.db import SCHEDULE_STATUS_CHOICES, SCHEDULE_FEEDBACK_CHOICES
from history.connector import connect


@connect()
class Schedule(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey('account.Company', on_delete=models.CASCADE)
    department = models.ForeignKey('account.Department', on_delete=models.CASCADE)
    start = models.DateTimeField()
    end = models.DateTimeField()
    shift_types = models.ManyToManyField('shift_type.ShiftType')
    preferences_deadline = models.DateTimeField()
    status = models.PositiveSmallIntegerField(choices=SCHEDULE_STATUS_CHOICES,
                                              default=SCHEDULE_STATUS_CHOICES.ENTERING_DETAILS)
    manual_input = models.BooleanField(default=False)
    collect_preferences = models.BooleanField(default=True)
    comment = models.TextField(null=True, blank=True, max_length=500)

    generic_data = JSONField(null=True, blank=True)

    def make_timestamp(self):
        stamp = ScheduleTimestamp()
        stamp.schedule = self
        stamp.status = self.status
        stamp.save()

    @property
    def related_trained_employees(self):
        ids = self.shift_types.all().values_list('trained_employees', flat=True).distinct()
        return Employee.objects.filter(id__in=ids)


@connect()
class ScheduleTimestamp(TimeStampedModel):
    timestamp = models.DateTimeField(auto_now_add=True)
    schedule = models.ForeignKey('Schedule', on_delete=models.CASCADE)
    status = models.PositiveSmallIntegerField(choices=SCHEDULE_STATUS_CHOICES,
                                              default=SCHEDULE_STATUS_CHOICES.ENTERING_DETAILS)


@connect()
class ScheduleFeedback(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey('account.Employee', on_delete=models.CASCADE, related_name='schedule_feedback')
    schedule = models.ForeignKey('Schedule', on_delete=models.CASCADE, related_name='employee_feedback')
    comment = models.TextField(max_length=5000, null=True, blank=True)
    rating = models.PositiveSmallIntegerField(choices=SCHEDULE_FEEDBACK_CHOICES)
    share_with_manager = models.BooleanField(default=True)
