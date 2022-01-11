import django_filters
from django.db.models import When, Case, IntegerField
from django_filters import rest_framework as filters

from account.models import Department
from constants.db import ABSENCE_STATUS_CHOICES, SCHEDULE_STATUS_CHOICES


class ScheduleListFilter(filters.FilterSet):
    status = django_filters.MultipleChoiceFilter(choices=SCHEDULE_STATUS_CHOICES)
    department = django_filters.ModelMultipleChoiceFilter(queryset=Department.objects.all())
    sortBy = filters.CharFilter(field_name='sortBy', method='filter_sort_by')

    def filter_sort_by(self, queryset, _name, value):
        asc_dec = '-' if self.request.query_params['sortDesc'] == 'true' else ''
        if value:

            if value == 'status':
                # translation hack
                queryset = queryset.annotate(schedule_status=Case(When(status=1, then=2),
                                                                  When(status=2, then=1),
                                                                  When(status=3, then=3),
                                                                  When(status=4, then=5),
                                                                  When(status=5, then=4),
                                                                  default=None,
                                                                  output_field=IntegerField()
                                                                  ))
                return queryset.order_by(f'{asc_dec}schedule_status')
            if value == 'start':
                return queryset.order_by(f'{asc_dec}start')
            if value == 'end':
                return queryset.order_by(f'{asc_dec}end')
            elif value == 'department':
                return queryset.order_by(f'{asc_dec}department__name')

        return queryset
