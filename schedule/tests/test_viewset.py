import collections
import datetime as dt
import random
from operator import attrgetter
from unittest.mock import patch, Mock

from django.test import TestCase
from django.utils import timezone
from freezegun import freeze_time
from model_bakery import baker

from account.models import Employee, Department
from account.tests.recipes import company_recipe, employee_recipe
from account.tests.util import create_user_session
from constants.db import COMPANY_ROLE_CHOICES
from constants.db import SCHEDULE_STATUS_CHOICES
from schedule.models import Schedule, ScheduleFeedback
from schedule.models import ScheduleTimestamp
from schedule.viewsets import ScheduleViewSet, ScheduleFeedbackViewSet
from shift.models import Shift
from shift_type.models import ShiftType


class TestScheduleViewSet(TestCase):

    def setUp(self):
        self.company = company_recipe.make()
        self.user = employee_recipe.make(company=self.company)
        self.viewset = ScheduleViewSet()

    @patch('schedule.viewsets.ScheduleQuerySet')
    def test_get_queryset(self, _schedule_query_set):
        user = baker.make(Employee, department=baker.make(Department))
        with patch.object(self.viewset, 'get_request_user') as request_user:
            request_user.return_value = user

            self.viewset.get_queryset()

            _schedule_query_set.assert_called_once_with(user)
            schedule_query_get_queryset = _schedule_query_set.return_value
            schedule_query_get_queryset.get_queryset.assert_called_once()

    @patch('schedule.viewsets.task_collecting_preferences_tasks')
    @patch('schedule.viewsets.send_email_on_collect_preferences_schedule')
    def test_collect_preferences(self, _send_email_on_collect_preferences_schedule, task_collecting_preferences_tasks):
        schedule = baker.make(Schedule, status=SCHEDULE_STATUS_CHOICES.ENTERING_DETAILS, collect_preferences=True)

        request = Mock()
        request.user = self.user

        with patch.object(self.viewset, 'get_object') as get_object:
            get_object.return_value = schedule

            self.viewset.collect_preferences(request)

            self.assertEqual(SCHEDULE_STATUS_CHOICES.COLLECTING_PREFERENCE, Schedule.objects.get(pk=schedule.pk).status)
            self.assertEqual(ScheduleTimestamp.objects.count(), 1)
            self.assertEqual(ScheduleTimestamp.objects.first().schedule, schedule)
            self.assertEqual(ScheduleTimestamp.objects.first().status, SCHEDULE_STATUS_CHOICES.COLLECTING_PREFERENCE)

            _send_email_on_collect_preferences_schedule.assert_called_once_with(self.user, schedule)
            task_collecting_preferences_tasks.delay.assert_called_once_with(schedule.pk)

    def test_request_schedule(self):
        schedule = baker.make(Schedule, status=SCHEDULE_STATUS_CHOICES.ENTERING_DETAILS, collect_preferences=False)

        request = Mock()
        request.user = self.user

        with patch.object(self.viewset, 'get_object') as get_object:
            get_object.return_value = schedule

            self.viewset.request_schedule(request)

            self.assertEqual(SCHEDULE_STATUS_CHOICES.PRODUCING_SCHEDULE, Schedule.objects.get(pk=schedule.pk).status)
            self.assertEqual(ScheduleTimestamp.objects.count(), 1)
            self.assertEqual(ScheduleTimestamp.objects.first().schedule, schedule)
            self.assertEqual(ScheduleTimestamp.objects.first().status, SCHEDULE_STATUS_CHOICES.PRODUCING_SCHEDULE)



    def test_stop_collecting_preferences(self):
        status_choice = random.choice([SCHEDULE_STATUS_CHOICES.ENTERING_DETAILS,
                                       SCHEDULE_STATUS_CHOICES.PRODUCING_SCHEDULE,
                                       SCHEDULE_STATUS_CHOICES.REVIEWING_SCHEDULE,
                                       SCHEDULE_STATUS_CHOICES.PUBLISHED])

        schedule_1 = baker.make(Schedule, status=status_choice)
        schedule_2 = baker.make(Schedule, status=SCHEDULE_STATUS_CHOICES.COLLECTING_PREFERENCE)

        with patch.object(self.viewset, 'get_object') as get_object:
            get_object.return_value = schedule_1
            self.viewset.stop_collecting_preferences()
            self.assertEqual(schedule_1.status, status_choice)

        with patch.object(self.viewset, 'get_object') as get_object:
            get_object.return_value = schedule_2
            self.viewset.stop_collecting_preferences()
            self.assertEqual(schedule_2.status, SCHEDULE_STATUS_CHOICES.PRODUCING_SCHEDULE)

    @patch('schedule.viewsets.task_publishing_tasks')
    @patch('schedule.viewsets.send_email_on_publish_schedule')
    def test_publish(self, _send_email_on_publish_schedule, task_publishing_tasks):
        schedule = baker.make(Schedule, status=SCHEDULE_STATUS_CHOICES.REVIEWING_SCHEDULE)

        request = Mock()
        request.user = self.user

        with patch.object(self.viewset, 'get_object') as get_object:
            get_object.return_value = schedule

            self.viewset.publish(request)

            self.assertEqual(SCHEDULE_STATUS_CHOICES.PUBLISHED, Schedule.objects.get(pk=schedule.pk).status)
            self.assertEqual(ScheduleTimestamp.objects.count(), 1)
            self.assertEqual(ScheduleTimestamp.objects.first().schedule, schedule)
            self.assertEqual(ScheduleTimestamp.objects.first().status, SCHEDULE_STATUS_CHOICES.PUBLISHED)

            _send_email_on_publish_schedule.assert_called_once_with(self.user, schedule)
            task_publishing_tasks.delay.assert_called_once_with(schedule.pk)

    @patch('schedule.viewsets.get_shift_queryset_for_schedule')
    def test_events(self, _queryset_for_schedule):
        schedule = baker.make(Schedule)

        shift_type_1 = baker.make(ShiftType, name='T1')
        shift_type_2 = baker.make(ShiftType, name='T2')
        shift_type_3 = baker.make(ShiftType, name='T3')

        shift_1 = baker.make(Shift, schedule=schedule, start=timezone.make_aware(dt.datetime(2020, 1, 1, 6, 0, 0)), end=timezone.make_aware(dt.datetime(2020, 1, 1, 14, 0, 0)), employees_needed=5, shift_type=shift_type_1)
        shift_2 = baker.make(Shift, schedule=schedule, start=timezone.make_aware(dt.datetime(2020, 1, 1, 14, 0, 0)), end=timezone.make_aware(dt.datetime(2020, 1, 1, 22, 0, 0)), employees_needed=15, shift_type=shift_type_2)
        shift_3 = baker.make(Shift, schedule=schedule, start=timezone.make_aware(dt.datetime(2020, 1, 1, 22, 0, 0)), end=timezone.make_aware(dt.datetime(2020, 1, 2, 6, 0, 0)), employees_needed=10, shift_type=shift_type_3)

        employee_1 = baker.make(Employee, department=baker.make(Department))
        employee_2 = baker.make(Employee, department=baker.make(Department))
        employee_3 = baker.make(Employee, department=baker.make(Department))
        employee_4 = baker.make(Employee, department=baker.make(Department))
        employee_5 = baker.make(Employee, department=baker.make(Department))
        employee_6 = baker.make(Employee, department=baker.make(Department))

        shift_1.employees_allocated.add(employee_1)
        shift_1.employees_allocated.add(employee_2)
        shift_1.employees_allocated.add(employee_3)
        shift_2.employees_allocated.add(employee_4)
        shift_3.employees_allocated.add(employee_5)
        shift_3.employees_allocated.add(employee_6)

        _queryset_for_schedule.return_value = Shift.objects.filter(id__in=[shift_1.pk, shift_2.pk, shift_3.pk])

        request = Mock()
        request.user = self.user
        request.query_params = dict(start='2020-12-09', end='2020-12-16')


        with patch.object(self.viewset, 'get_object') as get_object:
            with patch.object(self.viewset, 'get_request_user') as get_request_user:
                get_object.return_value = schedule
                get_request_user.return_value = self.user

                res = self.viewset.events(request).data

                expected_1 = collections.OrderedDict(id=str(shift_1.pk),
                                                     title='T1',
                                                     start='2020-01-01T06:00:00Z',
                                                     end='2020-01-01T14:00:00Z',
                                                     employees_needed=5,
                                                     shift_type=shift_type_1.pk
                                                     )

                expected_2 = collections.OrderedDict(id=str(shift_2.pk),
                                                     title='T2',
                                                     start='2020-01-01T14:00:00Z',
                                                     end='2020-01-01T22:00:00Z',
                                                     employees_needed=15,
                                                     employees_allocated=[employee_4.pk],
                                                     shift_type=shift_type_2.pk
                                                     )

                expected_3 = collections.OrderedDict(id=str(shift_3.pk),
                                                     title='T3',
                                                     start='2020-01-01T22:00:00Z',
                                                     end='2020-01-02T06:00:00Z',
                                                     employees_needed=10,
                                                     shift_type=shift_type_3.pk
                                                     )

                del res[0]['employees_allocated']
                del res[2]['employees_allocated']
                self.assertEqual(res[0], expected_1)
                self.assertEqual(res[1], expected_2)
                self.assertEqual(res[2], expected_3)

                _queryset_for_schedule.assert_called_once_with(self.user, schedule, dt.datetime(2020, 12, 8, 0, 0, 0),
                                                               dt.datetime(2020, 12, 17, 0, 0, 0))
                get_object.assert_called_once()
                get_request_user.assert_called_once()





class TestScheduleFeedbackViewSet(TestCase):

    def setUp(self):
        self.company = company_recipe.make()
        self.user = employee_recipe.make(company=self.company)
        self.viewset = ScheduleFeedbackViewSet()

    def test_get_all_queryset(self):
        schedule = baker.make(Schedule, status=SCHEDULE_STATUS_CHOICES.PUBLISHED)

        baker.make(ScheduleFeedback)
        baker.make(ScheduleFeedback)
        baker.make(ScheduleFeedback)

        with freeze_time("2020-01-01 09:30:00"):
            feedback_1 = baker.make(ScheduleFeedback, schedule=schedule)
        with freeze_time("2020-01-01 09:20:00"):
            feedback_2 = baker.make(ScheduleFeedback, schedule=schedule)
        with freeze_time("2020-01-01 09:00:00"):
            feedback_3 = baker.make(ScheduleFeedback, schedule=schedule)
        with freeze_time("2020-01-01 09:50:00"):
            feedback_4 = baker.make(ScheduleFeedback, schedule=schedule)
        with freeze_time("2020-01-01 19:00:00"):
            feedback_5 = baker.make(ScheduleFeedback, schedule=schedule)


        with patch.object(self.viewset, 'get_schedule') as get_schedule:
            get_schedule.return_value = schedule

            res = self.viewset.get_all_queryset()

            self.assertQuerysetEqual(res,
                                     [feedback_5.pk, feedback_4.pk, feedback_1.pk, feedback_2.pk, feedback_3.pk],
                                     ordered=True,
                                     transform=attrgetter('pk'))



    def test_get_list_queryset(self):
        feedback_1 = baker.make(ScheduleFeedback, share_with_manager=False)
        feedback_2 = baker.make(ScheduleFeedback, share_with_manager=True)
        feedback_3 = baker.make(ScheduleFeedback, share_with_manager=False)
        feedback_4 = baker.make(ScheduleFeedback, share_with_manager=False)
        feedback_5 = baker.make(ScheduleFeedback, share_with_manager=True)
        feedback_6 = baker.make(ScheduleFeedback, share_with_manager=False)
        feedback_7 = baker.make(ScheduleFeedback, share_with_manager=True)

        staff = baker.make(Employee, department=baker.make(Department), role=COMPANY_ROLE_CHOICES.STAFF)


        with patch.object(self.viewset, 'get_request_user') as get_request_user:
            get_request_user.return_value = staff
            with patch.object(self.viewset, 'get_all_queryset') as get_all_queryset:
                get_all_queryset.return_value = ScheduleFeedback.objects.all()

                res = self.viewset.get_list_queryset()

                self.assertQuerysetEqual(res,
                                         [feedback_2.pk, feedback_5.pk, feedback_7.pk],
                                         ordered=False,
                                         transform=attrgetter('pk'))

        with patch.object(self.viewset, 'get_request_user') as get_request_user:
            get_request_user.return_value = self.user
            res = self.viewset.get_list_queryset()
            self.assertFalse(res.exists())



    @patch('schedule.viewsets.get_schedule_feedback_stats')
    def test_feedback_stats(self, get_schedule_feedback_stats):

        with patch.object(self.viewset, 'get_all_queryset') as get_all_queryset:
            qs = Mock()
            get_all_queryset.return_value = qs
            get_schedule_feedback_stats.return_value = dict(percentages=2, average=5)

            res = self.viewset.feedback_stats()

            get_all_queryset.assert_called_once()
            get_schedule_feedback_stats.assert_called_once_with(qs)

            self.assertDictEqual(res.data, dict(percentages=2, average=5))



    def test_feedback_given(self):


        request = Mock()
        request.user = self.user

        feedback_1 = baker.make(ScheduleFeedback, employee=self.user)
        feedback_2 = baker.make(ScheduleFeedback)

        with patch.object(self.viewset, 'get_queryset') as get_queryset:
            get_queryset.return_value = ScheduleFeedback.objects.filter(pk=feedback_1.pk)

            res = self.viewset.feedback_given(request)
            self.assertDictEqual(res.data, dict(feedback_given=True))


        with patch.object(self.viewset, 'get_queryset') as get_queryset:
            get_queryset.return_value = ScheduleFeedback.objects.filter(pk=feedback_2.pk)

            res = self.viewset.feedback_given(request)
            self.assertDictEqual(res.data, dict(feedback_given=False))



    def test_get_schedule(self):
        status_choices = [SCHEDULE_STATUS_CHOICES.ENTERING_DETAILS, SCHEDULE_STATUS_CHOICES.COLLECTING_PREFERENCE,
                          SCHEDULE_STATUS_CHOICES.PRODUCING_SCHEDULE, SCHEDULE_STATUS_CHOICES.REVIEWING_SCHEDULE]

        schedule_1 = baker.make(Schedule, status=random.choice(status_choices))

        schedule_2 = baker.make(Schedule,  status=SCHEDULE_STATUS_CHOICES.PUBLISHED)

        with patch.object(self.viewset, 'get_schedule_queryset') as get_schedule_queryset:
            get_schedule_queryset.return_value = Schedule.objects.filter(id__in=[schedule_1.pk, schedule_2.pk])

            with patch.object(self.viewset, 'get_query_params') as get_query_params:
                get_query_params.return_value = dict(schedule=str(schedule_1.pk))
                res = self.viewset.get_schedule()
                self.assertEqual(res, None)


            with patch.object(self.viewset, 'get_query_params') as get_query_params:
                get_query_params.return_value = dict(schedule=str(schedule_2.pk))
                res = self.viewset.get_schedule()
                self.assertEqual(res, schedule_2)


    @patch('schedule.viewsets.ScheduleQuerySet')
    def test_get_schedule_queryset(self, _schedule_query_set):
        user = baker.make(Employee, department=baker.make(Department))
        with patch.object(self.viewset, 'get_request_user') as request_user:
            request_user.return_value = user

            self.viewset.get_schedule_queryset()

            _schedule_query_set.assert_called_once_with(user)
            schedule_query_get_queryset = _schedule_query_set.return_value
            schedule_query_get_queryset.get_queryset.assert_called_once()







