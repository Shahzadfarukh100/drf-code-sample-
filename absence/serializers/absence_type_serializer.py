from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from absence.models import EmployeeAbsenceType


class EmployeeAbsenceTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployeeAbsenceType
        fields = ('id',
                  'name',
                  'description',
                  'entitlement',
                  'period',
                  'submit_before_days',
                  'paid',
                  'duration')

    def validate_name(self, value):
        user = self.get_request_user()
        absence_type = EmployeeAbsenceType.objects.get_all_object().filter(company=user.company, name__iexact=value)

        if self.instance is not None:
            absence_type = absence_type.exclude(pk=self.instance.pk)

        absence_type = absence_type.first()

        if absence_type is not None:
            if absence_type.deleted_at is None:
                raise serializers.ValidationError(_('ABSENCE_TYPE_ALREADY_EXISTS'))
            else:
                raise serializers.ValidationError(_('ABSENCE_TYPE_WITH_THE_GIVEN_NAME_HAS_BEEN_ARCHIVED_RESTORE_IT_OR_TRY_WITH_ANOTHER_NAME'))
        return value

    def validate(self, data):
        user = self.get_request_user()
        data['company'] = user.company
        return data

    def get_request_user(self):
        return self.context.get('request').user


class EmployeeAbsenceTypeAsChoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployeeAbsenceType
        fields = ('id',
                  'name',
                  'paid',
                  'hourly')
        read_only_fields = fields
