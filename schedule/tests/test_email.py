import datetime as dt
from operator import attrgetter
from unittest.mock import call
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone
from django.utils.translation import ugettext as _
from django.utils.translation import ugettext_lazy as _
from model_bakery import baker

from account.models import Employee, Department
from schedule.emails import CollectPreferencesEmail, SchedulePublishedEmail
from schedule.models import Schedule
from shift_type.models import ShiftType


class TestCollectPreferencesEmail(TestCase):

    @patch('schedule.emails.MakeEmail.__init__')
    def test___init__(self, __init__):
        schedule = baker.make(Schedule)

        shift_types_1 = baker.make(ShiftType)
        shift_types_2 = baker.make(ShiftType)

        employee_1 = baker.make(Employee, department=baker.make(Department))
        employee_2 = baker.make(Employee, department=baker.make(Department))
        employee_3 = baker.make(Employee, department=baker.make(Department))
        employee_4 = baker.make(Employee, department=baker.make(Department))

        shift_types_1.trained_employees.add(employee_1, employee_2)
        shift_types_2.trained_employees.add(employee_3, employee_4)
        schedule.shift_types.add(shift_types_1, shift_types_2)

        employees = Employee.objects.filter(id__in=[employee_1.pk, employee_2.pk, employee_3.pk, employee_4.pk])

        email = CollectPreferencesEmail(schedule=schedule, iterable=employees)
        self.assertEqual(email.schedule, schedule)

        __init__.assert_called_once()
        self.assertQuerysetEqual(__init__.call_args_list[0][1]['iterable'],
                                 [employee_1.pk, employee_2.pk, employee_3.pk, employee_4.pk],
                                 ordered=False,
                                 transform=attrgetter('pk'))

    @patch('schedule.emails.MakeEmail.make_context')
    def test_make_context(self, _make_context):
        schedule = baker.make(Schedule)
        email = CollectPreferencesEmail(schedule=schedule, iterable=[])
        employee = baker.make(Employee, department=baker.make(Department), first_name='First Name')

        _make_context.return_value = dict()

        context = email.make_context(employee)
        self.assertDictEqual(context, dict(first_name='First Name', language='nb'))

        _make_context.assert_called_once()

    @patch('schedule.emails.formatted_date')
    @patch('schedule.emails.formatted_datetime')
    @patch('schedule.emails.local_datetime')
    def test_get_context(self, _local_datetime, _formatted_datetime, _formatted_date):
        schedule = baker.make(Schedule,
                              start=timezone.make_aware(dt.datetime(2020, 4, 25, 0, 0, 0)),
                              end=timezone.make_aware(dt.datetime(2020, 5, 30, 0, 0, 0)),
                              preferences_deadline=timezone.make_aware(dt.datetime(2020, 4, 30, 12, 30, 0)),
                              )

        _formatted_date.side_effect = ['25/04/2020', '30/05/2020']
        _local_datetime.return_value = timezone.make_aware(dt.datetime(2020, 4, 30, 14, 30, 0))
        _formatted_datetime.return_value = '30/04/2020 14:30'

        email = CollectPreferencesEmail(schedule=schedule, iterable=[])

        context = email.get_context()

        self.assertDictEqual(context, dict(start_date='25/04/2020', end_date='30/05/2020', deadline='30/04/2020 14:30',
                                           link=f'frontend_test/preferences/schedule/{schedule.id}'))

        _formatted_datetime.assert_called_once_with(timezone.make_aware(dt.datetime(2020, 4, 30, 14, 30, 0)))
        _local_datetime.assert_called_once_with(timezone.make_aware(dt.datetime(2020, 4, 30, 12, 30, 0)))

        self.assertEqual(_formatted_date.mock_calls,
                         [call(timezone.make_aware(dt.datetime(2020, 4, 25, 0, 0, 0))),
                          call(timezone.make_aware(dt.datetime(2020, 5, 30, 0, 0, 0)))])

    def test_subject(self):
        schedule = baker.make(Schedule)
        email = CollectPreferencesEmail(schedule=schedule, iterable=[])

        self.assertEqual(email.subject, _('SUBMIT_YOUR_PREFERENCES'))

    def test_template(self):
        schedule = baker.make(Schedule)
        email = CollectPreferencesEmail(schedule=schedule, iterable=[])

        self.assertEqual(email.template, 'COLLECT_PREFERENCES_EMAIL')


class TestSchedulePublishedEmail(TestCase):
    def test_subject(self):
        schedule = baker.make(Schedule)
        email = SchedulePublishedEmail(schedule=schedule, iterable=[])

        self.assertEqual(email.subject, _('A_NEW_SCHEDULE_HAS_BEEN_PUBLISHED'))

    def test_template(self):
        schedule = baker.make(Schedule)
        email = SchedulePublishedEmail(schedule=schedule, iterable=[])

        self.assertEqual(email.template, 'SCHEDULE_PUBLISHED_EMAIL')

    @patch('schedule.emails.formatted_date')
    @patch('schedule.emails.formatted_datetime')
    @patch('schedule.emails.local_datetime')
    def test_get_context(self, _local_datetime, _formatted_datetime, _formatted_date):
        schedule = baker.make(Schedule,
                              start=timezone.make_aware(dt.datetime(2020, 4, 25, 0, 0, 0)),
                              end=timezone.make_aware(dt.datetime(2020, 5, 30, 0, 0, 0)),
                              preferences_deadline=timezone.make_aware(dt.datetime(2020, 4, 30, 12, 30, 0)),
                              )

        _formatted_date.side_effect = ['25/04/2020', '30/05/2020']
        _local_datetime.return_value = timezone.make_aware(dt.datetime(2020, 4, 30, 14, 30, 0))
        _formatted_datetime.return_value = '30/04/2020 14:30'

        email = SchedulePublishedEmail(schedule=schedule, iterable=[])

        context = email.get_context()

        self.assertDictEqual(context, dict(start_date='25/04/2020', end_date='30/05/2020',
                                           link=f'frontend_test/schedule/{schedule.id}'))

        _formatted_datetime.assert_called_once_with(timezone.make_aware(dt.datetime(2020, 4, 30, 14, 30, 0)))
        _local_datetime.assert_called_once_with(timezone.make_aware(dt.datetime(2020, 4, 30, 12, 30, 0)))

        self.assertEqual(_formatted_date.mock_calls,
                         [call(timezone.make_aware(dt.datetime(2020, 4, 25, 0, 0, 0))),
                          call(timezone.make_aware(dt.datetime(2020, 5, 30, 0, 0, 0)))])
