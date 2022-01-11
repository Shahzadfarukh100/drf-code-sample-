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
from account.tests.recipes import company_recipe, employee_recipe
from account.tests.util import create_user_session
from schedule.models import Schedule, ScheduleFeedback
from schedule.serializers import ScheduleCreateSerializer, ScheduleRetrieveSerializer, ScheduleFeedbackCreateSerializer
from shift.models import Shift
from shift_type.models import ShiftType


class TestScheduleRetrieveSerializer(TestCase):

    def setUp(self):
        self.company = company_recipe.make()
        self.user = employee_recipe.make(company=self.company)
        request = Mock()
        request.user = self.user
        self.serializer = ScheduleRetrieveSerializer(context=dict(request=request))

    def test_get_event_start(self):

        schedule = baker.make(Schedule)


        baker.make(Shift, schedule=schedule, start=timezone.make_aware(dt.datetime(2020, 1, 2, 6, 0, 0)))
        baker.make(Shift, schedule=schedule, start=timezone.make_aware(dt.datetime(2020, 1, 1, 4, 0, 0)))
        baker.make(Shift, schedule=schedule, start=timezone.make_aware(dt.datetime(2020, 1, 1, 2, 0, 0)))
        baker.make(Shift, schedule=schedule, start=timezone.make_aware(dt.datetime(2020, 1, 5, 14, 0, 0)))
        baker.make(Shift, schedule=schedule, start=timezone.make_aware(dt.datetime(2020, 1, 5, 20, 0, 0)))
        baker.make(Shift, schedule=schedule, start=timezone.make_aware(dt.datetime(2020, 1, 10, 22, 0, 0)))

        res = self.serializer.get_event_start(schedule)

        self.assertEqual(res, timezone.make_aware(dt.datetime(2020, 1, 1, 2, 0, 0)))


    def test_get_event_end(self):

        schedule = baker.make(Schedule)


        baker.make(Shift, schedule=schedule, end=timezone.make_aware(dt.datetime(2020, 1, 2, 6, 0, 0)))
        baker.make(Shift, schedule=schedule, end=timezone.make_aware(dt.datetime(2020, 1, 1, 4, 0, 0)))
        baker.make(Shift, schedule=schedule, end=timezone.make_aware(dt.datetime(2020, 1, 1, 2, 0, 0)))
        baker.make(Shift, schedule=schedule, end=timezone.make_aware(dt.datetime(2020, 1, 10, 22, 0, 0)))
        baker.make(Shift, schedule=schedule, end=timezone.make_aware(dt.datetime(2020, 1, 5, 14, 0, 0)))
        baker.make(Shift, schedule=schedule, end=timezone.make_aware(dt.datetime(2020, 1, 5, 20, 0, 0)))

        res = self.serializer.get_event_end(schedule)

        self.assertEqual(res, timezone.make_aware(dt.datetime(2020, 1, 10, 22, 0, 0)))






class TestScheduleCreateSerializer(TestCase):

    def setUp(self):
        self.company = company_recipe.make()
        self.user = employee_recipe.make(company=self.company)
        request = Mock()
        request.user = self.user
        self.serializer = ScheduleCreateSerializer(context=dict(request=request))

    @freeze_time("2020-01-02 00:00:00")
    def test_validate_schedule_start(self):
        start = timezone.make_aware(dt.datetime(2020, 1, 1, 0, 0, 0))
        data = dict(collect_preferences=False, start=start)
        res = self.serializer.validate_schedule_start(data)
        self.assertIsNone(res)



        with self.assertRaises(ValidationError) as cm:
            start = timezone.make_aware(dt.datetime(2020, 1, 1, 0, 0, 0))
            data = dict(collect_preferences=True, start=start)
            self.serializer.validate_schedule_start(data)
        self.assertEqual(cm.exception.status_code, HTTP_400_BAD_REQUEST)
        self.assertEqual(cm.exception.detail,[_('START_DATE_MUST_BE_FUTURE_DATE')])


        start = timezone.make_aware(dt.datetime(2020, 1, 2, 0, 0, 0))
        data = dict(collect_preferences=True, start=start)
        res = self.serializer.validate_schedule_start(data)
        self.assertIsNone(res)


    def test_validated_schedule_date_range(self):
        with self.assertRaises(ValidationError) as cm:
            start = timezone.make_aware(dt.datetime(2020, 5, 1, 11, 0, 0))
            end = timezone.make_aware(dt.datetime(2020, 5, 1, 10, 0, 0))
            data = dict(start=start, end=end)
            self.serializer.validated_schedule_date_range(data)
        self.assertEqual(cm.exception.status_code, HTTP_400_BAD_REQUEST)
        self.assertEqual(cm.exception.detail, {'end': _('END_DATE_MUST_BE_AFTER_START_DATE')})


    def test_validate_schedule_duration(self):
        start = timezone.make_aware(dt.datetime(2020, 1, 1, 0, 0, 0))
        end = timezone.make_aware(dt.datetime(2021, 10, 1, 0, 0, 0))

        with self.assertRaises(ValidationError) as cm:
            data = dict(start=start, end=end)
            self.serializer.validate_schedule_duration(data)
        self.assertEqual(cm.exception.status_code, HTTP_400_BAD_REQUEST)
        self.assertEqual(cm.exception.detail, {'end': _('ONLY_370_DAYS_SCHEDULE_IS_ALLOWED')})

        start = timezone.make_aware(dt.datetime(2020, 1, 1, 0, 0, 0))
        end = timezone.make_aware(dt.datetime(2021, 1, 1, 0, 0, 0))
        data = dict(start=start, end=end)
        res = self.serializer.validate_schedule_duration(data)
        self.assertEqual(res, None)

    def test_validate_schedule_preferences_deadline(self):
        data = dict(collect_preferences=False, preferences_deadline=None)
        res = self.serializer.validate_schedule_preferences_deadline(data)
        self.assertEqual(res, None)

        with self.assertRaises(ValidationError) as cm:
            data = dict(collect_preferences=True, preferences_deadline=None)
            self.serializer.validate_schedule_preferences_deadline(data)
        self.assertEqual(cm.exception.status_code, HTTP_400_BAD_REQUEST)
        self.assertEqual(cm.exception.detail, {'preferences_deadline': _('PREFERENCES_DEADLINE_REQUIRED')})

        preferences_deadline = timezone.make_aware(dt.datetime(2020, 1, 1, 0, 0, 0))
        data = dict(collect_preferences=True, preferences_deadline=preferences_deadline)
        res = self.serializer.validate_schedule_preferences_deadline(data)
        self.assertEqual(res, None)

    def test_validate_overlapping_schedule(self):
        start = timezone.make_aware(dt.datetime(2020, 1, 1, 0, 0, 0))
        end = timezone.make_aware(dt.datetime(2020, 4, 10, 0, 0, 0))

        department_1 = baker.make(Department)
        department_2 = baker.make(Department)

        baker.make(Schedule, department=department_1, start=start, end=end)
        baker.make(Schedule, department=department_2, start=start, end=end)

        with self.assertRaises(ValidationError) as cm:
            start = timezone.make_aware(dt.datetime(2020, 1, 1, 0, 0, 0))
            end = timezone.make_aware(dt.datetime(2020, 4, 10, 0, 0, 0))
            data = dict(start=start, end=end, department=department_1)
            self.serializer.validate_overlapping_schedule(data)
        self.assertEqual(cm.exception.status_code, HTTP_400_BAD_REQUEST)
        self.assertEqual(cm.exception.detail, [_('AN_OVERLAPPING_SCHEDULE_ALREADY_EXIST_FOR_THIS_DEPARTMENT')])

        with self.assertRaises(ValidationError) as cm:
            start = timezone.make_aware(dt.datetime(2020, 4, 10, 0, 0, 0))
            end = timezone.make_aware(dt.datetime(2020, 4, 20, 0, 0, 0))
            data = dict(start=start, end=end, department=department_1)
            self.serializer.validate_overlapping_schedule(data)
        self.assertEqual(cm.exception.status_code, HTTP_400_BAD_REQUEST)
        self.assertEqual(cm.exception.detail, [_('AN_OVERLAPPING_SCHEDULE_ALREADY_EXIST_FOR_THIS_DEPARTMENT')])

        with self.assertRaises(ValidationError) as cm:
            start = timezone.make_aware(dt.datetime(2019, 12, 10, 0, 0, 0))
            end = timezone.make_aware(dt.datetime(2020, 2, 10, 0, 0, 0))
            data = dict(start=start, end=end, department=department_1)
            self.serializer.validate_overlapping_schedule(data)
        self.assertEqual(cm.exception.status_code, HTTP_400_BAD_REQUEST)
        self.assertEqual(cm.exception.detail, [_('AN_OVERLAPPING_SCHEDULE_ALREADY_EXIST_FOR_THIS_DEPARTMENT')])

        with self.assertRaises(ValidationError) as cm:
            start = timezone.make_aware(dt.datetime(2020, 2, 10, 0, 0, 0))
            end = timezone.make_aware(dt.datetime(2020, 3, 20, 0, 0, 0))
            data = dict(start=start, end=end, department=department_1)
            self.serializer.validate_overlapping_schedule(data)
        self.assertEqual(cm.exception.status_code, HTTP_400_BAD_REQUEST)
        self.assertEqual(cm.exception.detail, [_('AN_OVERLAPPING_SCHEDULE_ALREADY_EXIST_FOR_THIS_DEPARTMENT')])

        with self.assertRaises(ValidationError) as cm:
            start = timezone.make_aware(dt.datetime(2020, 1, 1, 0, 0, 0))
            end = timezone.make_aware(dt.datetime(2020, 4, 10, 0, 0, 0))
            data = dict(start=start, end=end, department=department_2)
            self.serializer.validate_overlapping_schedule(data)
        self.assertEqual(cm.exception.status_code, HTTP_400_BAD_REQUEST)
        self.assertEqual(cm.exception.detail, [_('AN_OVERLAPPING_SCHEDULE_ALREADY_EXIST_FOR_THIS_DEPARTMENT')])

        start = timezone.make_aware(dt.datetime(2020, 4, 15, 0, 0, 0))
        end = timezone.make_aware(dt.datetime(2020, 4, 20, 0, 0, 0))
        data = dict(start=start, end=end, department=department_2)
        res = self.serializer.validate_overlapping_schedule(data)
        self.assertEqual(res, None)


    def test_validate(self):
        with patch.object(self.serializer, 'get_request_user') as get_request_user:
            get_request_user.return_value = self.user
            with patch.object(self.serializer, 'validate_schedule_start') as validate_schedule_start:
                with patch.object(self.serializer, 'validated_schedule_date_range') as validated_schedule_date_range:
                    with patch.object(self.serializer, 'validate_schedule_duration') as validate_schedule_duration:
                        with patch.object(self.serializer, 'validate_overlapping_schedule') as validate_overlapping_schedule:
                            with patch.object(self.serializer, 'validate_schedule_preferences_deadline') as validate_schedule_preferences_deadline:

                                data = dict(manual_input=False)
                                res = self.serializer.validate(data)
                                self.assertDictEqual(res, dict(manual_input=False, company=self.company))

                                validate_schedule_start.assert_called_once()
                                validated_schedule_date_range.assert_called_once()
                                validate_schedule_duration.assert_called_once()
                                validate_overlapping_schedule.assert_called_once()
                                validate_schedule_preferences_deadline.assert_called_once()



        with patch.object(self.serializer, 'get_request_user') as get_request_user:
            get_request_user.return_value = self.user
            with patch.object(self.serializer, 'validate_schedule_start') as validate_schedule_start:
                with patch.object(self.serializer, 'validated_schedule_date_range') as validated_schedule_date_range:
                    with patch.object(self.serializer, 'validate_schedule_duration') as validate_schedule_duration:
                        with patch.object(self.serializer, 'validate_overlapping_schedule') as validate_overlapping_schedule:
                            with patch.object(self.serializer, 'validate_schedule_preferences_deadline') as validate_schedule_preferences_deadline:

                                data = dict(manual_input=True)
                                res = self.serializer.validate(data)
                                self.assertDictEqual(res, dict(manual_input=True, company=self.company, status=4))

                                validate_schedule_start.assert_called_once()
                                validated_schedule_date_range.assert_called_once()
                                validate_schedule_duration.assert_called_once()
                                validate_overlapping_schedule.assert_called_once()
                                validate_schedule_preferences_deadline.assert_called_once()

    @patch('schedule.serializers.task_create_shifts_for_schedule')
    def test_create(self, task_create_shifts_for_schedule):

        task = Mock()
        task.task_id='1'

        task_create_shifts_for_schedule.return_value = task





        department = baker.make(Department)
        shift_type_1 = baker.make(ShiftType, name='T1')
        shift_type_2 = baker.make(ShiftType, name='T2')

        data = {
            "department": department,
            "start": "2021-01-01 00:00",
            "end": "2021-03-01 00:00",
            "shift_types": [
                shift_type_1, shift_type_2
            ],
            "preferences_deadline": "2020-01-01 00:00",
            "manual_input": True,
            "collect_preferences": False,
            "comment": "",
            "generic_data": {},
            "company": self.company
        }

        with patch.object(self.serializer, 'get_request_user') as get_request_user:
            with patch.object(self.serializer, 'get_request_shifts') as get_request_shifts:
                with patch.object(self.serializer, 'create_shift_type_snapshot') as create_shift_type_snapshot:
                    get_request_shifts.return_value = dict()
                    get_request_user.return_value = self.user

                    res = self.serializer.create(data)

                    self.assertEqual(Schedule.objects.count(), 1)
                    self.assertEqual(Schedule.objects.first(), res)

                    task_create_shifts_for_schedule.delay.assert_called_once_with({}, str(res.pk), self.user.timezone)
                    get_request_shifts.assert_called_once()
                    create_shift_type_snapshot.assert_called_once_with(data)


    def test_create_shift_type_snapshot(self):
        shift_type_1 = baker.make(ShiftType)
        shift_type_2 = baker.make(ShiftType)
        shift_type_3 = baker.make(ShiftType)

        shift_type_1.trained_employees.add(baker.make(Employee, department=baker.make(Department), resigned=False))
        shift_type_2.trained_employees.add(baker.make(Employee, department=baker.make(Department), resigned=True))
        shift_type_3.trained_employees.add(baker.make(Employee, department=baker.make(Department), resigned=False))

        self.assertEqual(3, ShiftType.objects.all().count())

        data = dict(shift_types=[shift_type_1, shift_type_2, shift_type_3])
        self.serializer.create_shift_type_snapshot(data)
        res = data['shift_types']

        self.assertEqual(1, res[0].trained_employees.all().count())
        self.assertEqual(0, res[1].trained_employees.all().count())
        self.assertEqual(1, res[2].trained_employees.all().count())

        self.assertEqual(6, ShiftType.objects.all().count())
        self.assertEquals(res[0].parent_shift_type, shift_type_1)
        self.assertEquals(res[1].parent_shift_type, shift_type_2)
        self.assertEquals(res[2].parent_shift_type, shift_type_3)



class TestScheduleFeedbackCreateSerializer(TestCase):

    def setUp(self):
        self.company = company_recipe.make()
        self.user = employee_recipe.make(company=self.company)
        request = Mock()
        request.user = self.user
        self.serializer = ScheduleFeedbackCreateSerializer(context=dict(request=request))

    def test_validate(self):
        schedule = baker.make(Schedule)
        schedule_2 = baker.make(Schedule)
        baker.make(ScheduleFeedback, employee=self.user, schedule=schedule)

        with self.assertRaises(ValidationError) as cm:
            data = dict(schedule=schedule, employee=self.user)
            self.serializer.validate(data)
        self.assertEqual(cm.exception.status_code, HTTP_400_BAD_REQUEST)
        self.assertEqual(cm.exception.detail, [_('SCHEDULE_FEEDBACK_ALREADY_GIVEN')])

        data = dict(schedule=schedule_2, employee=self.user)
        res = self.serializer.validate(data)
        self.assertDictEqual(res, data)