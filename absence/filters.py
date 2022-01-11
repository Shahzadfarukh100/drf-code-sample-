import django_filters
from django_filters import rest_framework as filters

from account.models import Employee
from constants.db import ABSENCE_STATUS_CHOICES, DURATION


class EmployeeAbsenceFilter(filters.FilterSet):
    submitted_for = django_filters.ModelMultipleChoiceFilter(queryset=Employee.objects.all())
    status = django_filters.MultipleChoiceFilter(choices=ABSENCE_STATUS_CHOICES)
    absence_duration = django_filters.MultipleChoiceFilter(choices=DURATION, field_name='absence_type__duration')
    sortBy = filters.CharFilter(field_name='sortBy', method='filter_sort_by')

    def filter_sort_by(self, queryset, _name, value):

        asc_dec = '-' if self.request.query_params['sortDesc'] == 'true' else ''
        if value:

            if value == 'submitted_by':
                return queryset.order_by(f'{asc_dec}submitted_by')
            if value == 'submitted_for':
                return queryset.order_by(f'{asc_dec}submitted_for')
            if value == 'submitted_to':
                return queryset.order_by(f'{asc_dec}submitted_to')
            if value == 'title':
                return queryset.order_by(f'{asc_dec}subject')
            if value == 'start':
                return queryset.order_by(f'{asc_dec}start')
            if value == 'end':
                return queryset.order_by(f'{asc_dec}end')

        return queryset


class EmployeeAbsenceTypeFilter(filters.FilterSet):
    archived = django_filters.BooleanFilter(field_name='deleted_at', lookup_expr='isnull', exclude=True)
    duration = django_filters.MultipleChoiceFilter(choices=DURATION)
    sortBy = filters.CharFilter(field_name='sortBy', method='filter_sort_by')

    def filter_sort_by(self, queryset, _name, value):

        asc_dec = '-' if self.request.query_params['sortDesc'] == 'true' else ''
        if value:

            if value == 'name':
                return queryset.order_by(f'{asc_dec}name')
        return queryset


class GeneralAbsenceFilter(filters.FilterSet):
    status = django_filters.MultipleChoiceFilter(choices=ABSENCE_STATUS_CHOICES)
    sortBy = filters.CharFilter(field_name='sortBy', method='filter_sort_by')

    def filter_sort_by(self, queryset, _name, value):

        asc_dec = '-' if self.request.query_params['sortDesc'] == 'true' else ''
        if value:

            if value == 'title':
                return queryset.order_by(f'{asc_dec}subject')
            if value == 'start':
                return queryset.order_by(f'{asc_dec}start')
            if value == 'end':
                return queryset.order_by(f'{asc_dec}end')

        return queryset

