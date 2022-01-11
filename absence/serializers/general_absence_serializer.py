from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers
import datetime as dt

from absence.models import GeneralAbsence
from absence.permissions_utils import can_general_absence_update, can_general_absence_delete, \
    can_general_absence_restore
from absence.signals import general_absence_created
from absence.utils import get_leaves_duration
from account.models import Department
from account.serializers import EmployeeAsChoiceSerializer, DepartmentChoiceSerializer


class GeneralAbsenceSerializer(serializers.ModelSerializer):
    department_choices = DepartmentChoiceSerializer(read_only=True, many=True, source='department')
    submitted_by = EmployeeAsChoiceSerializer(read_only=True)
    end = serializers.DateTimeField(source='get_end')
    duration = serializers.SerializerMethodField(read_only=True)
    can_update = serializers.SerializerMethodField(read_only=True)
    can_delete = serializers.SerializerMethodField(read_only=True)
    can_restore = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = GeneralAbsence
        fields = ('id',
                  'subject',
                  'body',
                  'status',
                  'start',
                  'end',
                  'department',
                  'department_choices',
                  'duration',
                  'submitted_by',
                  'can_update',
                  'can_delete',
                  'can_restore'
                  )

    @staticmethod
    def get_duration(obj):
        days = get_leaves_duration(obj.start, obj.end)
        return str(days) + ' ' + str(_('DAY')) if days == 1 else str(days) + ' ' + str(_('DAYS'))

    def get_request_user(self):
        return self.context.get('request').user

    def get_can_update(self, obj):
        user = self.get_request_user()
        return can_general_absence_update(user, obj)

    def get_can_delete(self, obj):
        user = self.get_request_user()
        return can_general_absence_delete(user, obj)

    def get_can_restore(self, obj):
        user = self.get_request_user()
        return can_general_absence_restore(user, obj)


class GeneralAbsenceWriteBaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = GeneralAbsence
        fields = ('id',
                  'subject',
                  'body',
                  'status',
                  'start',
                  'end',
                  'department'
                  )

    def get_request_user(self):
        return self.context.get('request').user

    @staticmethod
    def set_end_date(data):
        end = data.get('end')
        data['end'] = end + dt.timedelta(days=1)

    def validate(self, data):
        start = data.get('start')
        end = data.get('end')
        if start > end:
            raise serializers.ValidationError(_('END_DATE_CAN_NOT_BE_A_DATE_BEFORE_START_DATE'))
        return data

    @staticmethod
    def add_departments(instance, departments=None):
        if departments is not None:
            for dept in departments:
                instance.department.add(dept)

    @staticmethod
    def remove_departments(instance, departments=None):
        if departments is not None:
            for dept in departments:
                instance.department.remove(dept)


class GeneralAbsenceCreateSerializer(GeneralAbsenceWriteBaseSerializer):
    department = serializers.ListField(write_only=True, required=False)

    def get_departments(self, data):
        user = self.get_request_user()

        if user.is_manager_admin_or_manager():
            return data.pop('department', None)

        if user.is_staff_():
            data.pop('department', None)
            return [user.department]

    def create(self, validated_data):
        user = self.get_request_user()
        departments = self.get_departments(validated_data)
        self.set_end_date(validated_data)

        validated_data['company'] = user.company
        validated_data['submitted_by'] = user
        instance = super().create(validated_data)

        self.add_departments(instance, departments)
        general_absence_created.send(sender=self.__class__, instance=instance)

        return instance


class GeneralAbsenceUpdateSerializer(GeneralAbsenceWriteBaseSerializer):
    department = serializers.ListField(write_only=True, required=False)

    class Meta:
        model = GeneralAbsence
        fields = ('id',
                  'subject',
                  'body',
                  'status',
                  'start',
                  'end',
                  'department'
                  )

    def get_departments(self, instance, data):
        user = self.get_request_user()

        if instance.submitted_by.is_staff_():
            data.pop('department', None)
            return [str(instance.submitted_by.department.id)]

        elif user.is_manager_admin_or_manager():
            return data.pop('department', None)

        elif user.is_staff_():
            data.pop('department', None)
            return [str(user.department.id)]

    def update(self, instance, validated_data):

        self.set_end_date(validated_data)
        departments = self.get_departments(instance, validated_data)
        instance = super().update(instance, validated_data)

        old = [str(x) for x in instance.department.all().values_list('id', flat=True)]
        new = departments
        adding = Department.objects.filter(pk__in=[x for x in new if x not in old])
        removing = Department.objects.filter(pk__in=[x for x in old if x not in new])
        self.add_departments(instance, adding)
        self.remove_departments(instance, removing)

        return instance
