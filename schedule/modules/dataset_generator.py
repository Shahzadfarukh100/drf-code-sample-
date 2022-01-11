from django.utils.translation import gettext_lazy as _

from account.modules.dataset_generator import BaseDataSetGenerator
from constants.db import SCHEDULE_STATUS_CHOICES
from helpers.formatting import formatted_date, local_date, formatted_datetime, local_datetime


class ScheduleListViewDataSetGenerator(BaseDataSetGenerator):
    def __init__(self, queryset):
        queryset = queryset.prefetch_related('department')
        super().__init__(queryset, title='schedule_list')

    @staticmethod
    def get_instance_data_row(instance):
        shift_type_str = ', '.join(list(instance.shift_types.all().order_by('name').values_list('name', flat=True)))
        return [
            str(SCHEDULE_STATUS_CHOICES[instance.status]),
            formatted_date(local_date(instance.start)),
            formatted_date(local_date(instance.end)),
            instance.department.name,
            shift_type_str,
            formatted_datetime(local_datetime(instance.preferences_deadline)) if instance.collect_preferences else '',
            _('YES') if instance.manual_input else _('NO'),
            _('YES') if instance.collect_preferences else _('NO')
        ]

    @staticmethod
    def get_header_row():
        return [
            _('STATUS'),
            _('START_DATE'),
            _('END_DATE'),
            _('DEPARTMENT'),
            _('SHIFT_TYPES'),
            _('PREFERENCE_DEADLINE'),
            _('MANUAL_INPUT'),
            _('COLLECT_PREFERENCE')
        ]
