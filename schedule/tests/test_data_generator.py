import datetime as dt

from django.test import TestCase
from django.utils import timezone
from django.utils.translation import ugettext as _
from django.utils.translation import ugettext_lazy as _
from model_bakery import baker

from account.models import Department
from constants.db import SCHEDULE_STATUS_CHOICES
from schedule.models import Schedule
from schedule.modules.dataset_generator import ScheduleListViewDataSetGenerator
from shift_type.models import ShiftType


class TestScheduleListViewDataSetGenerator(TestCase):

    def test__get_header_row(self):
        header = ScheduleListViewDataSetGenerator.get_header_row()

        self.assertListEqual(header, [
            _('STATUS'),
            _('START_DATE'),
            _('END_DATE'),
            _('DEPARTMENT'),
            _('SHIFT_TYPES'),
            _('PREFERENCE_DEADLINE'),
            _('MANUAL_INPUT'),
            _('COLLECT_PREFERENCE')
        ])

    def test__get_instance_data_row_for_collect_preferences(self):
        schedule = baker.make(Schedule,
                                start=timezone.make_aware(dt.datetime(2020, 1, 1, 0, 0, 0)),
                                end=timezone.make_aware(dt.datetime(2020, 5, 15, 0, 0, 0)),
                                preferences_deadline=timezone.make_aware(dt.datetime(2020, 1, 15, 10, 30, 0)),
                                department=baker.make(Department, name='Department Name'),
                                status=SCHEDULE_STATUS_CHOICES.COLLECTING_PREFERENCE,
                                manual_input=False,
                                collect_preferences=True

                                )

        schedule.shift_types.add(baker.make(ShiftType, name='Shift Type 1'),
                                   baker.make(ShiftType, name='Shift Type 2'))

        data_row = ScheduleListViewDataSetGenerator.get_instance_data_row(schedule)
        expected = [
            str(_('COLLECTING_PREFERENCE')),
            '2020-01-01',
            '2020-05-15',
            'Department Name',
            'Shift Type 1, Shift Type 2',
            '2020-01-15 10:30',
            _('NO'),
            _('YES')

        ]

        self.assertListEqual(data_row, expected)


    def test__get_instance_data_row_for_manual_input(self):
        schedule = baker.make(Schedule,
                                start=timezone.make_aware(dt.datetime(2020, 1, 1, 0, 0, 0)),
                                end=timezone.make_aware(dt.datetime(2020, 5, 15, 0, 0, 0)),
                                preferences_deadline=timezone.make_aware(dt.datetime(2020, 1, 15, 10, 30, 0)),
                                department=baker.make(Department, name='Department Name'),
                                status=SCHEDULE_STATUS_CHOICES.REVIEWING_SCHEDULE,
                                manual_input=True,
                                collect_preferences=False

                                )

        schedule.shift_types.add(baker.make(ShiftType, name='Shift Type 1'),
                                   baker.make(ShiftType, name='Shift Type 2'))

        data_row = ScheduleListViewDataSetGenerator.get_instance_data_row(schedule)
        expected = [
            str(_('REVIEWING_SCHEDULE')),
            '2020-01-01',
            '2020-05-15',
            'Department Name',
            'Shift Type 1, Shift Type 2',
            '',
            _('YES'),
            _('NO')

        ]

        self.assertListEqual(data_row, expected)
