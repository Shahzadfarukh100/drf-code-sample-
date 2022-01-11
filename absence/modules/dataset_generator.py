from django.utils.translation import gettext_lazy as _

from absence.models import EmployeeAbsenceType, GeneralAbsence
from absence.utils import get_leaves_duration_string, get_leave_start, get_leave_end
from account.modules.dataset_generator import BaseDataSetGenerator
from constants.db import ABSENCE_ENTITLEMENT_PERIOD_CHOICE, ABSENCE_STATUS_CHOICES, DURATION
from helpers.formatting import formatted_datetime, formatted_date, local_datetime, local_date


class EmployeeAbsenceListViewDataSetGenerator(BaseDataSetGenerator):
    def __init__(self, queryset):
        queryset = queryset.prefetch_related('absence_type',
                                             'submitted_for',
                                             'submitted_by',
                                             'submitted_to', )
        super().__init__(queryset, title='employee_absence_list')

    @staticmethod
    def get_instance_data_row(instance):
        duration = get_leaves_duration_string(instance)
        start = get_leave_start(instance)
        end = get_leave_end(instance)

        return [
            instance.submitted_by.get_full_name(),
            instance.submitted_for.get_full_name(),
            instance.submitted_to.get_full_name() if instance.submitted_to is not None else '',
            instance.subject,
            start,
            end,
            duration,
            str(ABSENCE_STATUS_CHOICES[instance.status]),
            instance.submitted_for.department.name,
            formatted_datetime(local_datetime(instance.created)),
            instance.absence_type.name
        ]

    @staticmethod
    def get_header_row():
        return [
            _('SUBMITTED_BY'),
            _('SUBMITTED_FOR'),
            _('SUBMITTED_TO'),
            _('TITLE'),
            _('START'),
            _('END'),
            _('DURATION'),
            _('STATUS'),
            _('DEPARTMENT'),
            _('SUBMITTED_ON'),
            _('ABSENCE_TYPE'),
        ]


class AbsenceTypeListViewDataSetGenerator(BaseDataSetGenerator):
    def __init__(self, queryset):
        super().__init__(queryset, title='absence_type_list')

    @staticmethod
    def get_instance_data_row(instance: EmployeeAbsenceType):
        return [
            instance.name,
            instance.description,
            instance.entitlement,
            str(ABSENCE_ENTITLEMENT_PERIOD_CHOICE[instance.period]),
            instance.submit_before_days,
            _('YES') if instance.paid else _('NO'),
            str(DURATION[instance.duration])
        ]

    @staticmethod
    def get_header_row():
        return [
            _('NAME'),
            _('DESCRIPTION'),
            _('ENTITLEMENT'),
            _('ABSENCE_PERIOD'),
            _('SUBMIT_BEFORE_DAYS'),
            _('PAID'),
            _('ABSENCE_DURATION'),
        ]


class GeneralAbsenceListViewDataSetGenerator(BaseDataSetGenerator):
    def __init__(self, queryset):
        queryset = queryset.prefetch_related(
            'department',
            'submitted_by'
        )
        super().__init__(queryset, title='general_absence_list')

    @staticmethod
    def get_instance_data_row(instance: GeneralAbsence):
        departments = ", ".join(instance.department.all().order_by('name').values_list('name', flat=True))
        return [
            instance.subject,
            instance.body,
            str(ABSENCE_STATUS_CHOICES[instance.status]),
            instance.submitted_by.get_full_name(),
            formatted_date(local_date(instance.start)),
            formatted_date(local_date(instance.end)),
            departments
        ]

    @staticmethod
    def get_header_row():
        return [
            _('TITLE'),
            _('BODY'),
            _('STATUS'),
            _('SUBMITTED_BY'),
            _('START'),
            _('END'),
            _('DEPARTMENT')
        ]
