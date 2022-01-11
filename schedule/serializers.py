
from django.db.models import Q, Min, Max
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from account.serializers import DepartmentSerializer, EmployeeAsChoiceSerializer
from constants.db import SCHEDULE_STATUS_CHOICES
from core.mixins import ValidateDepartmentMixin, GenericDataFieldMixin
from core.tasks.schedule import (
    task_create_shifts_for_schedule
)
from helpers.serializers import ShiftTypeAsChoicesSerializer
from schedule.models import Schedule, ScheduleFeedback
from shift.serializers import ShiftAsEventSerializer
from shift.utils import get_shift_queryset
from shift_type.models import ShiftType


class ScheduleRetrieveSerializer(serializers.ModelSerializer):
    # events = serializers.SerializerMethodField(read_only=True)
    shift_types = ShiftTypeAsChoicesSerializer(many=True)
    department = DepartmentSerializer()
    event_start = serializers.SerializerMethodField()
    event_end = serializers.SerializerMethodField()

    class Meta:
        model = Schedule
        fields = ('id', 'department', 'shift_types', 'manual_input',
                  'collect_preferences', 'start', 'end', 'status', 'comment',
                  'event_start', 'event_end')

    def get_request_user(self):
        return self.context['request'].user


    @staticmethod
    def get_event_start(obj):
        qs = obj.shifts.aggregate(start=Min('start'))
        return qs['start']

    @staticmethod
    def get_event_end(obj):
        qs = obj.shifts.aggregate(end=Max('end'))
        return qs['end']

class ScheduleCreateSerializer(ValidateDepartmentMixin, GenericDataFieldMixin, serializers.ModelSerializer):
    class Meta:
        model = Schedule
        fields = ('id', 'department', 'shift_types', 'preferences_deadline', 'manual_input',
                  'collect_preferences', 'start', 'end', 'comment', 'generic_data')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.task_id = None

    def get_request_shifts(self):
        return self.context['request'].data.get('shifts')

    def get_request_user(self):
        return self.context['request'].user

    @staticmethod
    def validate_schedule_start(data):
        start = data.get('start')
        collect_preferences = data.get('collect_preferences')

        if collect_preferences and start < timezone.now():
            raise serializers.ValidationError(_(f'START_DATE_MUST_BE_FUTURE_DATE'))


    @staticmethod
    def validated_schedule_date_range(data):
        start = data.get('start')
        end = data.get('end')

        if end < start:
            raise serializers.ValidationError({'end': _('END_DATE_MUST_BE_AFTER_START_DATE')})



    @staticmethod
    def validate_schedule_duration(data):
        start = data.get('start')
        end = data.get('end')
        if (end - start).days > 370:
            raise serializers.ValidationError({
                'end': _('ONLY_370_DAYS_SCHEDULE_IS_ALLOWED')
            })

    @staticmethod
    def validate_schedule_preferences_deadline(data):
        collect_preferences = data.get('collect_preferences', False)
        preferences_deadline = data.get('preferences_deadline', None)
        if collect_preferences and preferences_deadline is None:
            raise serializers.ValidationError({
                'preferences_deadline': _('PREFERENCES_DEADLINE_REQUIRED')
            })

    @staticmethod
    def validate_overlapping_schedule(data):
        start = data.get('start')
        end = data.get('end')
        department = data.get('department')

        schedule_qs = Schedule.objects.filter(department=department)
        schedule_qs = schedule_qs.filter(
            Q(end__range=(start, end)) |
            Q(start__range=(start, end)) |
            Q(start__lte=start, end__gte=end)
        )

        if schedule_qs.exists():
            raise serializers.ValidationError(_(f'AN_OVERLAPPING_SCHEDULE_ALREADY_EXIST_FOR_THIS_DEPARTMENT'))

    def validate(self, data):

        user = self.get_request_user()
        data['company'] = user.company

        if data.get('manual_input'):
            data['status'] = SCHEDULE_STATUS_CHOICES.REVIEWING_SCHEDULE

        self.validate_schedule_start(data)
        self.validated_schedule_date_range(data)
        self.validate_schedule_duration(data)
        self.validate_overlapping_schedule(data)
        self.validate_schedule_preferences_deadline(data)

        return data

    @staticmethod
    def create_shift_type_snapshot(data):
        shift_type_snapshots= []

        shift_types = data.get('shift_types')
        for t in shift_types:

            s_t = ShiftType.objects.create(
                department=t.department,
                name=t.name,
                comment=t.comment,
                generic_data=t.generic_data,
                parent_shift_type=t
            )
            s_t.trained_employees.set(t.trained_employees.filter(resigned=False))
            shift_type_snapshots.append(s_t)

        data['shift_types'] = shift_type_snapshots


    def create(self, data):
        user = self.get_request_user()
        shifts = self.get_request_shifts()
        self.create_shift_type_snapshot(data)
        instance = super().create(data)
        task = task_create_shifts_for_schedule.delay(shifts, str(instance.pk), user.timezone)
        self.task_id = task.task_id

        return instance

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['task_id'] = self.task_id
        return representation


class ScheduleListSerializer(serializers.ModelSerializer):
    department = DepartmentSerializer()

    class Meta:
        model = Schedule
        fields = ('id', 'department', 'company', 'start', 'end', 'status')

    def create(self, validated_data):
        pass

    def update(self, instance, validated_data):
        pass


class ScheduleAsChoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Schedule
        fields = ('id', 'start', 'end', 'status')

    def create(self, validated_data):
        pass

    def update(self, instance, validated_data):
        pass


class ScheduleFeedbackCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScheduleFeedback
        fields = ('id', 'employee', 'schedule', 'comment', 'rating', 'share_with_manager')

    def validate(self, data):

        if ScheduleFeedback.objects.filter(employee=data.get('employee'), schedule=data.get('schedule')).exists():
            raise serializers.ValidationError(_('SCHEDULE_FEEDBACK_ALREADY_GIVEN'))

        return data


class ScheduleFeedbackListSerializer(serializers.ModelSerializer):
    employee = EmployeeAsChoiceSerializer()

    class Meta:
        model = ScheduleFeedback
        fields = ('id', 'created', 'employee', 'schedule', 'comment', 'rating')
