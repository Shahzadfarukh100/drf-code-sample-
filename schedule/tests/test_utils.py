from operator import attrgetter

from django.test import TestCase
from freezegun import freeze_time
from model_bakery import baker
import collections
import datetime as dt
from unittest.mock import patch, Mock

from django.test import TestCase
from django.utils import timezone
from django.utils.translation import ugettext as _
from django.utils.translation import ugettext_lazy as _
from freezegun import freeze_time
from model_bakery import baker
from rest_framework.exceptions import ValidationError
from rest_framework.status import *

from account.models import Employee, Department
from account.tests.util import create_user_session
from constants.db import SCHEDULE_STATUS_CHOICES
from schedule.models import Schedule, ScheduleFeedback
from schedule.serializers import ScheduleCreateSerializer, ScheduleRetrieveSerializer, ScheduleFeedbackCreateSerializer
from shift.models import Shift
from shift_type.models import ShiftType
from account.models import Employee, Department
from schedule.models import ScheduleFeedback, Schedule
from schedule.utils import get_schedule_feedback_stats, add_employee_to_schedules_shift_types_training, \
    send_email_on_collect_preferences_schedule, send_email_on_publish_schedule
from shift_type.models import ShiftType


class TestAddEmployeeToSchedulesShiftTypeTraining(TestCase):

    @freeze_time("2020-01-01 00:00:00")
    def test_add_employee_to_schedules_shift_types_training__schedule_end_date_as_current(self):
        department = baker.make(Department)
        employee = baker.make(Employee, department=department)

        shift_type = baker.make(ShiftType)
        shift_type_schedule = baker.make(ShiftType, parent_shift_type=shift_type)

        schedule = baker.make(Schedule, end=timezone.make_aware(dt.datetime(2020, 1, 1, 0, 0, 0)),
                              department=department)
        schedule.shift_types.add(shift_type_schedule)

        self.assertFalse(shift_type_schedule.trained_employees.filter(id=employee.id).exists())

        shift_type.trained_employees.add(employee)
        add_employee_to_schedules_shift_types_training(employee)

        self.assertTrue(shift_type_schedule.trained_employees.filter(id=employee.id).exists())

    @freeze_time("2020-01-01 00:00:00")
    def test_add_employee_to_schedules_shift_types_training__schedule_other_department(self):
        department = baker.make(Department)
        employee = baker.make(Employee, department=department)

        shift_type = baker.make(ShiftType)
        shift_type_schedule = baker.make(ShiftType, parent_shift_type=shift_type)

        schedule = baker.make(Schedule, end=timezone.make_aware(dt.datetime(2020, 1, 1, 0, 0, 0)),
                              department=baker.make(Department))
        schedule.shift_types.add(shift_type_schedule)

        self.assertFalse(shift_type_schedule.trained_employees.filter(id=employee.id).exists())

        shift_type.trained_employees.add(employee)
        add_employee_to_schedules_shift_types_training(employee)

        self.assertFalse(shift_type_schedule.trained_employees.filter(id=employee.id).exists())

    @freeze_time("2020-01-01 00:00:00")
    def test_add_employee_to_schedules_shift_types_training__schedule_end_date_future(self):
        department = baker.make(Department)
        employee = baker.make(Employee, department=department)

        shift_type = baker.make(ShiftType)
        shift_type_schedule = baker.make(ShiftType, parent_shift_type=shift_type)

        schedule = baker.make(Schedule, end=timezone.make_aware(dt.datetime(2020, 5, 1, 0, 0, 0)),
                              department=department)
        schedule.shift_types.add(shift_type_schedule)

        self.assertFalse(shift_type_schedule.trained_employees.filter(id=employee.id).exists())

        shift_type.trained_employees.add(employee)
        add_employee_to_schedules_shift_types_training(employee)

        self.assertTrue(shift_type_schedule.trained_employees.filter(id=employee.id).exists())


    @freeze_time("2020-01-01 00:00:00")
    def test_add_employee_to_schedules_shift_types_training__schedule_end_date_past(self):
        department = baker.make(Department)
        employee = baker.make(Employee, department=department)

        shift_type = baker.make(ShiftType)
        shift_type_schedule = baker.make(ShiftType, parent_shift_type=shift_type)

        schedule = baker.make(Schedule, end=timezone.make_aware(dt.datetime(2019, 10, 1, 0, 0, 0)),
                              department=department)
        schedule.shift_types.add(shift_type_schedule)

        self.assertFalse(shift_type_schedule.trained_employees.filter(id=employee.id).exists())

        shift_type.trained_employees.add(employee)
        add_employee_to_schedules_shift_types_training(employee)

        self.assertFalse(shift_type_schedule.trained_employees.filter(id=employee.id).exists())

    @freeze_time("2020-01-01 00:00:00")
    def test_add_employee_to_schedules_shift_types_training__employee_not_trained_in_original_shift_type(self):
        department = baker.make(Department)
        employee = baker.make(Employee, department=department)

        shift_type = baker.make(ShiftType)
        shift_type_schedule = baker.make(ShiftType, parent_shift_type=shift_type)

        schedule = baker.make(Schedule, end=timezone.make_aware(dt.datetime(2020, 1, 1, 0, 0, 0)),
                              department=department)
        schedule.shift_types.add(shift_type_schedule)

        self.assertFalse(shift_type_schedule.trained_employees.filter(id=employee.id).exists())
        add_employee_to_schedules_shift_types_training(employee)
        self.assertFalse(shift_type_schedule.trained_employees.filter(id=employee.id).exists())


class TestSendEmailOnCollectPreferencesSchedule(TestCase):

    @patch('schedule.utils.CollectPreferencesEmail')
    @patch('schedule.utils.send_welcome_email')
    def test_send_email_on_collect_preferences_schedule(self, _send_welcome_email, _CollectPreferencesEmail):
        shift_type_1 = baker.make(ShiftType, name='T1')
        shift_type_2 = baker.make(ShiftType, name='T2')
        shift_type_3 = baker.make(ShiftType, name='T3')

        employee_1 = baker.make(Employee, department=baker.make(Department), is_active=True)
        employee_2 = baker.make(Employee, department=baker.make(Department))
        employee_3 = baker.make(Employee, department=baker.make(Department))
        employee_4 = baker.make(Employee, department=baker.make(Department), is_active=True)
        employee_5 = baker.make(Employee, department=baker.make(Department))
        employee_6 = baker.make(Employee, department=baker.make(Department), is_active=True)

        shift_type_1.trained_employees.add(employee_1,employee_2,employee_3)
        shift_type_2.trained_employees.add(employee_4,employee_5)
        shift_type_2.trained_employees.add(employee_6)

        schedule = baker.make(Schedule, status=SCHEDULE_STATUS_CHOICES.ENTERING_DETAILS, collect_preferences=False)
        schedule.shift_types.add(shift_type_1, shift_type_2, shift_type_3)

        request_user = baker.make(Employee, department=baker.make(Department))
        preference_email = _CollectPreferencesEmail.return_value

        send_email_on_collect_preferences_schedule(request_user, schedule)

        _send_welcome_email.assert_called_once()
        _CollectPreferencesEmail.assert_called_once()
        preference_email.send.assert_called_once()

        self.assertEqual(_CollectPreferencesEmail.call_args_list[0][1]['schedule'], schedule)
        self.assertQuerysetEqual(_CollectPreferencesEmail.call_args_list[0][1]['iterable'],
                                 [employee_2.pk,employee_3.pk,employee_5.pk],
                                 ordered=False,
                                 transform=attrgetter('pk'))


        self.assertEqual(_send_welcome_email.call_args_list[0][0][0], request_user)
        self.assertQuerysetEqual(_send_welcome_email.call_args_list[0][0][1],
                                 [employee_2.pk,employee_3.pk,employee_5.pk],
                                 ordered=False,
                                 transform=attrgetter('pk'))


class TestSendEmailOnPublishSchedule(TestCase):

    @patch('schedule.utils.SchedulePublishedEmail')
    @patch('schedule.utils.send_welcome_email')
    def test_send_email_on_publish_schedule(self, _send_welcome_email, _SchedulePublishedEmail):
        shift_type_1 = baker.make(ShiftType, name='T1')
        shift_type_2 = baker.make(ShiftType, name='T2')
        shift_type_3 = baker.make(ShiftType, name='T3')

        employee_1 = baker.make(Employee, department=baker.make(Department), is_active=True)
        employee_2 = baker.make(Employee, department=baker.make(Department))
        employee_3 = baker.make(Employee, department=baker.make(Department))
        employee_4 = baker.make(Employee, department=baker.make(Department), is_active=True)
        employee_5 = baker.make(Employee, department=baker.make(Department))
        employee_6 = baker.make(Employee, department=baker.make(Department), is_active=True)

        shift_type_1.trained_employees.add(employee_1,employee_2,employee_3)
        shift_type_2.trained_employees.add(employee_4,employee_5)
        shift_type_2.trained_employees.add(employee_6)

        schedule = baker.make(Schedule, status=SCHEDULE_STATUS_CHOICES.ENTERING_DETAILS, collect_preferences=False)
        schedule.shift_types.add(shift_type_1, shift_type_2, shift_type_3)

        request_user = baker.make(Employee, department=baker.make(Department))
        publish_email = _SchedulePublishedEmail.return_value

        send_email_on_publish_schedule(request_user, schedule)

        _send_welcome_email.assert_called_once()
        _SchedulePublishedEmail.assert_called_once()
        publish_email.send.assert_called_once()

        self.assertEqual(_SchedulePublishedEmail.call_args_list[0][1]['schedule'], schedule)
        self.assertQuerysetEqual(_SchedulePublishedEmail.call_args_list[0][1]['iterable'],
                                 [employee_2.pk,employee_3.pk,employee_5.pk],
                                 ordered=False,
                                 transform=attrgetter('pk'))


        self.assertEqual(_send_welcome_email.call_args_list[0][0][0], request_user)
        self.assertQuerysetEqual(_send_welcome_email.call_args_list[0][0][1],
                                 [employee_2.pk,employee_3.pk,employee_5.pk],
                                 ordered=False,
                                 transform=attrgetter('pk'))


class TestGetScheduleFeedbackStats(TestCase):

    def test_get_schedule_feedback_stats(self):
        baker.make(ScheduleFeedback, rating=5)
        baker.make(ScheduleFeedback, rating=5)
        baker.make(ScheduleFeedback, rating=5)
        baker.make(ScheduleFeedback, rating=2)
        baker.make(ScheduleFeedback, rating=2)
        baker.make(ScheduleFeedback, rating=3)
        baker.make(ScheduleFeedback, rating=3)
        baker.make(ScheduleFeedback, rating=3)
        baker.make(ScheduleFeedback, rating=5)
        baker.make(ScheduleFeedback, rating=5)
        baker.make(ScheduleFeedback, rating=4)
        baker.make(ScheduleFeedback, rating=4)

        employee_feedback = ScheduleFeedback.objects.all()

        res = get_schedule_feedback_stats(employee_feedback)

        expected = dict(percentages=[41, 16, 25, 16, 0], average=3.8333333333333335)

        self.assertDictEqual(res, expected)
