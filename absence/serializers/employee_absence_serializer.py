import logging
from datetime import timedelta

from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from absence.models import EmployeeAbsence, EmployeeAbsenceComment
from absence.serializers.absence_base_serializer import BaseAbsenceSerializer
from absence.serializers.absence_type_serializer import EmployeeAbsenceTypeAsChoiceSerializer
from absence.signals import absence_created
from absence.utils import (get_leaves_duration,
                           notify_subordinate_about_absence_status_updated,
                           get_leaves_duration_string,
                           get_entitlement_overflow_interval_week,
                           get_entitlement_overflow_interval_month,
                           get_entitlement_overflow_interval_year)
from account.models import Employee
from account.serializers import EmployeeAsChoiceSerializer
from constants.db import ABSENCE_STATUS_CHOICES, ABSENCE_ENTITLEMENT_PERIOD_CHOICE, DURATION
from employee_shift.utils import is_employee_shift_exist_for_employee

logger = logging.getLogger(__name__)



class EmployeeAbsenceCommentSerializer(serializers.ModelSerializer):
    commented_by = EmployeeAsChoiceSerializer(read_only=True)

    class Meta:
        model = EmployeeAbsenceComment
        fields = ('id', 'comment', 'status', 'commented_by', 'created')


class EmployeeAbsenceListSerializer(serializers.ModelSerializer):
    duration = serializers.SerializerMethodField()
    end = serializers.DateTimeField(source='get_end')
    submitted_for = EmployeeAsChoiceSerializer(read_only=True)
    submitted_by = EmployeeAsChoiceSerializer(read_only=True)
    submitted_to = EmployeeAsChoiceSerializer(read_only=True)
    absence_type = EmployeeAbsenceTypeAsChoiceSerializer(read_only=True)
    comment = EmployeeAbsenceCommentSerializer(many=True, source='get_comments', read_only=True)


    class Meta:
        model = EmployeeAbsence
        fields = ('id',
                  'subject',
                  'submitted_for',
                  'submitted_by',
                  'submitted_to',
                  'status',
                  'start',
                  'end',
                  'absence_type',
                  'duration',
                  'is_created_for_past',
                  'comment')


    @staticmethod
    def get_duration(obj):
        return get_leaves_duration_string(obj)

class EmployeeAbsenceCreateSerializer(BaseAbsenceSerializer):
    submitted_for = serializers.PrimaryKeyRelatedField(allow_null=True, queryset=Employee.objects.all())
    ignore_shift_overlap = serializers.BooleanField(default=False)
    absence_duration = serializers.ChoiceField(choices=DURATION, required=True, write_only=True)
    comment = serializers.CharField(write_only=True, required=False, allow_blank=True)


    class Meta:
        model = EmployeeAbsence
        fields = ('id', 'subject', 'submitted_for', 'submitted_to', 'start',
                  'end', 'absence_type', 'comment', 'ignore_shift_overlap', 'absence_duration')


    def validate(self, data):
        self.validate_dates(data)
        self.set_end_date(data)
        self.set_employee_relations(data)
        self.validate_submit_before(data)
        self.validate_overlap(data)
        self.validate_shift_overlap(data)
        self.set_status(data)
        self.set_company(data)
        return data

    def create(self, validated_data):
        validated_data.pop('ignore_shift_overlap', False)
        validated_data.pop('absence_duration', False)
        comment = validated_data.pop('comment', None)
        instance = super(EmployeeAbsenceCreateSerializer, self).create(validated_data)
        self.create_comment(instance, comment)
        absence_created.send(sender=self.__class__, instance=instance)

        return instance

    def create_comment(self, instance, comment):
        user = self.get_request_user()
        EmployeeAbsenceComment.objects.create(absence=instance,
                                              comment=comment,
                                              status=instance.status,
                                              commented_by=user)




class EmployeeAbsenceStatusUpdateSerializer(serializers.ModelSerializer):
    status = serializers.IntegerField(required=True)
    comment = serializers.CharField(required=False, allow_blank=True)
    ignore_shift_overlap = serializers.BooleanField(default=False)

    class Meta:
        model = EmployeeAbsence
        fields = ('status', 'comment', 'ignore_shift_overlap')

    def validate(self, data):
        self.validate_shift_overlap(data)
        self.validate_balance(data)
        return data

    def validate_shift_overlap(self, data):

        leave = self.instance
        ignore_shift_overlap = data.get('ignore_shift_overlap', False)
        status = data.get('status')
        if status == ABSENCE_STATUS_CHOICES.APPROVED and not ignore_shift_overlap:
            is_shift = is_employee_shift_exist_for_employee(leave.submitted_for, leave.start, leave.end)
            if is_shift:
                raise serializers.ValidationError(
                    {'ignore_shift_overlap':
                         _('EMPLOYEE_SHIFT_EXIST_FOR_THIS_DURATION.ARE_YOU_STILL_WANT_TO_APPROVE_ABSENCE')})

        data.pop('ignore_shift_overlap', False)

    def validate_balance(self, data):
        status = data.get('status')
        if status == ABSENCE_STATUS_CHOICES.APPROVED and self.instance.absence_type.entitlement > 0:

            if self.instance.absence_type.period == ABSENCE_ENTITLEMENT_PERIOD_CHOICE.PER_WEEK:
                self.validate_balance_per_week()

            elif self.instance.absence_type.period == ABSENCE_ENTITLEMENT_PERIOD_CHOICE.PER_MONTH:
                self.validate_balance_per_month()

            elif self.instance.absence_type.period == ABSENCE_ENTITLEMENT_PERIOD_CHOICE.PER_YEAR:
                self.validate_balance_per_year()

    def update(self, instance, data):
        status_before_save = instance.status
        instance = super().update(instance, data)
        comment = self.create_comment(data)

        if status_before_save != instance.status:
            self.send_notifications(comment)
        return instance

    def create_comment(self, validated_data):
        comment = validated_data.pop('comment', None)
        return EmployeeAbsenceComment.objects.create(absence=self.instance,
                                                     comment=comment,
                                                     status=self.instance.status,
                                                     commented_by=self.context.get('request').user)

    def send_notifications(self, comment):
        notify_subordinate_about_absence_status_updated(self.instance, comment)

    def validate_balance_per_week(self):
        res = get_entitlement_overflow_interval_week(self.instance)
        if res is not None:
            consumed = res.get('consumed')
            start = res.get('start')
            end = res.get('end')

            raise serializers.ValidationError(_(
                f'ALREADY_HAVE_AVAILED_{consumed}_ABSENCES_FOR_WEEK_FROM_{start}_TO_{end}.MAXIMUM_ENTITLEMENT_FOR_THIS_WEEK_IS_{self.instance.absence_type.entitlement}'))

    def validate_balance_per_month(self):
        res = get_entitlement_overflow_interval_month(self.instance)
        if res is not None:
            consumed = res.get('consumed')
            start = res.get('start')
            end = res.get('end')

            raise serializers.ValidationError(_(
                f'ALREADY_HAVE_AVAILED_{consumed}_ABSENCES_FOR_MONTH_FROM_{start}_TO_{end}.MAXIMUM_ENTITLEMENT_FOR_THIS_MONTH_IS_{self.instance.absence_type.entitlement}'))

    def validate_balance_per_year(self):
        res = get_entitlement_overflow_interval_year(self.instance)
        if res is not None:
            consumed = res.get('consumed')
            start = res.get('start')
            end = res.get('end')

            raise serializers.ValidationError(_(
                f'ALREADY_HAVE_AVAILED_{consumed}_ABSENCES_FOR_YEAR_FROM_{start}_TO_{end}.MAXIMUM_ENTITLEMENT_FOR_THIS_YEAR_IS_{self.instance.absence_type.entitlement}'))
