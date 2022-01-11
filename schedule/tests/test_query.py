import datetime as dt
import random
from operator import attrgetter
from unittest.mock import Mock
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone
from freezegun import freeze_time
from model_bakery import baker
from rest_framework.exceptions import PermissionDenied
from rest_framework.status import *

from account.models import Company
from account.models import Employee, Department
from account.tests.util import create_user_session
from constants.db import COMPANY_ROLE_CHOICES
from constants.db import SCHEDULE_STATUS_CHOICES
from schedule.models import Schedule
from schedule.models import ScheduleTimestamp, ScheduleFeedback
from schedule.query import ScheduleQuerySet
from schedule.viewsets import ScheduleViewSet, ScheduleFeedbackViewSet
from shift.models import Shift
from shift_type.models import ShiftType


class TestScheduleQuerySet(TestCase):

    def test_init(self):
        department = baker.make(Department)

        schedule_1 = baker.make(Schedule, department=baker.make(Department), company=baker.make(Company))
        schedule_2 = baker.make(Schedule, department=baker.make(Department), company=baker.make(Company))
        schedule_3 = baker.make(Schedule, department=baker.make(Department), company=baker.make(Company))
        schedule_4 = baker.make(Schedule, department=baker.make(Department), company=baker.make(Company))

        employee = baker.make(Employee, department=department, role=COMPANY_ROLE_CHOICES.EMPLOYEE)
        staff = baker.make(Employee, department=department, role=COMPANY_ROLE_CHOICES.STAFF)
        manager = baker.make(Employee, department=department, role=COMPANY_ROLE_CHOICES.MANAGER)
        admin_manager = baker.make(Employee, department=department, role=COMPANY_ROLE_CHOICES.MANAGER_ADMIN)

        query_1 = ScheduleQuerySet(employee)
        query_2 = ScheduleQuerySet(staff)
        query_3 = ScheduleQuerySet(manager)
        query_4 = ScheduleQuerySet(admin_manager)

        self.assertEqual(query_1.user, employee)
        self.assertEqual(query_2.user, staff)
        self.assertEqual(query_3.user, manager)
        self.assertEqual(query_4.user, admin_manager)

        self.assertQuerysetEqual(random.choice([query_1.qs, query_2.qs, query_3.qs, query_4.qs]),
                                 [schedule_1.pk, schedule_2.pk, schedule_3.pk, schedule_4.pk],
                                 ordered=False,
                                 transform=attrgetter('pk'))

    @patch('schedule.query.ScheduleQuerySet.queryset_for_user_active_department')
    @patch('schedule.query.ScheduleQuerySet.has_user_active_department')
    def test_queryset_for_manager_admin_or_manager(self, _active_department, _queryset_active_department):
        user = baker.make(Employee, department=baker.make(Department))

        with patch.object(user, 'is_manager_admin_or_manager') as is_manager_admin_or_manager:

            is_manager_admin_or_manager.return_value = False
            _active_department.return_value = True

            query = ScheduleQuerySet(user)
            query.queryset_for_manager_admin_or_manager()

            is_manager_admin_or_manager.assert_called_once()
            _active_department.assert_not_called()
            _queryset_active_department.assert_not_called()

        with patch.object(user, 'is_manager_admin_or_manager') as is_manager_admin_or_manager:
            is_manager_admin_or_manager.reset_mock()
            _active_department.reset_mock()
            _queryset_active_department.reset_mock()

            is_manager_admin_or_manager.return_value = True
            _active_department.return_value = False

            query = ScheduleQuerySet(user)
            query.queryset_for_manager_admin_or_manager()

            is_manager_admin_or_manager.assert_called_once()
            _active_department.assert_called_once()
            _queryset_active_department.assert_not_called()

        with patch.object(user, 'is_manager_admin_or_manager') as is_manager_admin_or_manager:
            is_manager_admin_or_manager.reset_mock()
            _active_department.reset_mock()
            _queryset_active_department.reset_mock()

            is_manager_admin_or_manager.return_value = True
            _active_department.return_value = True

            query = ScheduleQuerySet(user)
            query.queryset_for_manager_admin_or_manager()

            is_manager_admin_or_manager.assert_called_once()
            _active_department.assert_called_once()
            _queryset_active_department.assert_called_once()


    @patch('schedule.query.ScheduleQuerySet.queryset_for_user_department')
    def test_queryset_for_staff(self, _queryset_for_user_department):
        user = baker.make(Employee, department=baker.make(Department))
        with patch.object(user, 'is_staff_') as is_staff_:
            is_staff_.return_value = False

            query = ScheduleQuerySet(user)
            query.queryset_for_staff()

            _queryset_for_user_department.assert_not_called()

        with patch.object(user, 'is_staff_') as is_staff_:
            _queryset_for_user_department.reset_mock()

            is_staff_.return_value = True

            query = ScheduleQuerySet(user)
            query.queryset_for_staff()

            _queryset_for_user_department.assert_called_once_with()

    def test_has_user_active_department(self):
        user_1 = baker.make(Employee, department=baker.make(Department))
        user_2 = baker.make(Employee, department=baker.make(Department), active_department=baker.make(Department))

        query_1 = ScheduleQuerySet(user_1)
        query_2 = ScheduleQuerySet(user_2)

        self.assertFalse(query_1.has_user_active_department())
        self.assertTrue(query_2.has_user_active_department())

    def test_queryset_for_user_active_department(self):
        department_1 = baker.make(Department)
        department_2 = baker.make(Department)

        user_1 = baker.make(Employee, department=baker.make(Department), active_department=department_1)
        user_2 = baker.make(Employee, department=baker.make(Department), active_department=department_2)

        schedule_1 = baker.make(Schedule, department=department_1)
        schedule_2 = baker.make(Schedule, department=department_1)
        schedule_3 = baker.make(Schedule, department=department_1)
        schedule_4 = baker.make(Schedule, department=department_2)
        schedule_5 = baker.make(Schedule, department=department_2)
        schedule_6 = baker.make(Schedule, department=department_2)
        baker.make(Schedule, department=baker.make(Department))
        baker.make(Schedule, department=baker.make(Department))
        baker.make(Schedule, department=baker.make(Department))
        baker.make(Schedule, department=baker.make(Department))

        query_1 = ScheduleQuerySet(user_1)
        query_2 = ScheduleQuerySet(user_2)

        query_1.queryset_for_user_active_department()
        query_2.queryset_for_user_active_department()

        self.assertQuerysetEqual(query_1.qs,
                                 [schedule_1.pk, schedule_2.pk, schedule_3.pk],
                                 ordered=False,
                                 transform=attrgetter('pk'))

        self.assertQuerysetEqual(query_2.qs,
                                 [schedule_4.pk, schedule_5.pk, schedule_6.pk],
                                 ordered=False,
                                 transform=attrgetter('pk'))


    def test_queryset_sorting(self):

        with freeze_time("2020-01-01 09:30:00"):
            department_1 = baker.make(Department, name='A')
            department_4 = baker.make(Department, name='D')
            department_7 = baker.make(Department, name='G')

        with freeze_time("2020-01-01 00:20:00"):
            department_2 = baker.make(Department, name='B')
            department_5 = baker.make(Department, name='E')
            department_8 = baker.make(Department, name='H')

        with freeze_time("2020-01-02 09:00:00"):
            department_3 = baker.make(Department, name='C')
            department_6 = baker.make(Department, name='F')
            department_9 = baker.make(Department, name='I')

        schedule_1 = baker.make(Schedule, department=department_1)
        schedule_2 = baker.make(Schedule, department=department_2)
        schedule_3 = baker.make(Schedule, department=department_3)
        schedule_4 = baker.make(Schedule, department=department_4)
        schedule_5 = baker.make(Schedule, department=department_5)
        schedule_6 = baker.make(Schedule, department=department_6)
        schedule_7 = baker.make(Schedule, department=department_7)
        schedule_8 = baker.make(Schedule, department=department_8)
        schedule_9 = baker.make(Schedule, department=department_9)

        query = ScheduleQuerySet(None)
        query.queryset_sorting()



        self.assertQuerysetEqual(query.qs,
                                 [schedule_9.pk, schedule_8.pk, schedule_7.pk,
                                  schedule_6.pk, schedule_5.pk,schedule_4.pk,
                                  schedule_3.pk, schedule_2.pk, schedule_1.pk],
                                 ordered=True,
                                 transform=attrgetter('pk'))



    def test_get_user_involved_schedules(self):
        status_choices = [SCHEDULE_STATUS_CHOICES.ENTERING_DETAILS, SCHEDULE_STATUS_CHOICES.COLLECTING_PREFERENCE,
                          SCHEDULE_STATUS_CHOICES.PRODUCING_SCHEDULE, SCHEDULE_STATUS_CHOICES.REVIEWING_SCHEDULE]

        schedule_1 = baker.make(Schedule, status=random.choice(status_choices))
        schedule_2 = baker.make(Schedule, status=SCHEDULE_STATUS_CHOICES.PUBLISHED)
        schedule_3 = baker.make(Schedule, status=SCHEDULE_STATUS_CHOICES.PUBLISHED)
        schedule_4 = baker.make(Schedule, status=SCHEDULE_STATUS_CHOICES.PUBLISHED)

        shift_1 = baker.make(Shift, schedule=schedule_1)
        shift_2 = baker.make(Shift, schedule=schedule_2)
        shift_3 = baker.make(Shift, schedule=schedule_3)
        shift_4 = baker.make(Shift, schedule=schedule_4)


        user_1 = baker.make(Employee, department=baker.make(Department))
        user_2 = baker.make(Employee, department=baker.make(Department))


        shift_1.employees_allocated.add(user_1)
        shift_2.employees_allocated.add(user_1)
        shift_4.employees_allocated.add(user_1)


        shift_1.employees_allocated.add(user_2)
        shift_3.employees_allocated.add(user_2)
        shift_4.employees_allocated.add(user_2)

        query_1 = ScheduleQuerySet(user_1)
        query_2 = ScheduleQuerySet(user_2)
        sc_1 = query_1.get_user_involved_schedules()
        sc_2 = query_2.get_user_involved_schedules()


        self.assertListEqual(list(sc_1), [schedule_2.pk, schedule_4.pk])
        self.assertListEqual(list(sc_2), [schedule_3.pk, schedule_4.pk])



    @patch('schedule.query.ScheduleQuerySet.get_user_involved_schedules')
    def test_queryset_for_user_department(self, _get_user_involved_schedules):

        department_1= baker.make(Department)
        department_2= baker.make(Department)


        user_1 = baker.make(Employee, department=department_1)
        user_2 = baker.make(Employee, department=department_2)

        schedule_1 = baker.make(Schedule, department=department_1)
        schedule_2 = baker.make(Schedule, department=department_1)
        schedule_3 = baker.make(Schedule, department=department_2)
        schedule_4 = baker.make(Schedule, department=department_2)
        schedule_5 = baker.make(Schedule, department=baker.make(Department))
        schedule_6 = baker.make(Schedule, department=baker.make(Department))

        baker.make(Schedule, department=baker.make(Department))
        baker.make(Schedule, department=baker.make(Department))
        baker.make(Schedule, department=baker.make(Department))
        baker.make(Schedule, department=baker.make(Department))
        baker.make(Schedule, department=baker.make(Department))


        _get_user_involved_schedules.return_value = [schedule_5.pk, schedule_6.pk]

        query_1 = ScheduleQuerySet(user_1)
        query_1.queryset_for_user_department()


        self.assertQuerysetEqual(query_1.qs,
                                 [schedule_1.pk, schedule_2.pk, schedule_5.pk,schedule_6.pk],
                                 ordered=False,
                                 transform=attrgetter('pk'))
        _get_user_involved_schedules.assert_called_once()


        _get_user_involved_schedules.reset_mock()
        query_2 = ScheduleQuerySet(user_2)
        query_2.queryset_for_user_department()
        self.assertQuerysetEqual(query_2.qs,
                                 [schedule_3.pk, schedule_4.pk, schedule_5.pk,schedule_6.pk],
                                 ordered=False,
                                 transform=attrgetter('pk'))
        _get_user_involved_schedules.assert_called_once()








    @patch('schedule.query.ScheduleQuerySet.queryset_for_user_department')
    def test_queryset_for_employee_for_other_then_employee(self, _queryset_for_user_department):
        schedule_1 = baker.make(Schedule, department=baker.make(Department))
        schedule_2 = baker.make(Schedule, department=baker.make(Department))
        schedule_3 = baker.make(Schedule, department=baker.make(Department))
        schedule_4 = baker.make(Schedule, department=baker.make(Department))
        schedule_5 = baker.make(Schedule, department=baker.make(Department))
        schedule_6 = baker.make(Schedule, department=baker.make(Department))


        department = baker.make(Department)

        staff = baker.make(Employee, department=department, role=COMPANY_ROLE_CHOICES.STAFF)
        manager = baker.make(Employee, department=department, role=COMPANY_ROLE_CHOICES.MANAGER)
        admin_manager = baker.make(Employee, department=department, role=COMPANY_ROLE_CHOICES.MANAGER_ADMIN)


        user = random.choice([staff, manager, admin_manager])
        query = ScheduleQuerySet(user)
        query.queryset_for_employee()

        self.assertQuerysetEqual(query.qs,
                                 [schedule_1.pk, schedule_2.pk, schedule_3.pk,
                                  schedule_4.pk, schedule_5.pk, schedule_6.pk],
                                 ordered=False,
                                 transform=attrgetter('pk'))
        _queryset_for_user_department.assert_not_called()



    @patch('schedule.query.ScheduleQuerySet.queryset_for_user_department')
    def test_queryset_for_employee_for_employee(self, _queryset_for_user_department):
        department = baker.make(Department)

        end_1 = timezone.make_aware(dt.datetime(2020, 1, 1, 5, 0, 0))
        end_2 = timezone.make_aware(dt.datetime(2020, 1, 1, 10, 0, 0))

        schedule_1 = baker.make(Schedule, end=end_2, status=SCHEDULE_STATUS_CHOICES.PUBLISHED)
        schedule_2 = baker.make(Schedule, end=end_2, status=SCHEDULE_STATUS_CHOICES.PUBLISHED)
        schedule_5 = baker.make(Schedule, end=end_2, status=SCHEDULE_STATUS_CHOICES.PUBLISHED)
        schedule_6 = baker.make(Schedule, end=end_2, status=SCHEDULE_STATUS_CHOICES.PUBLISHED)
        baker.make(Schedule, end=end_1, status=SCHEDULE_STATUS_CHOICES.PUBLISHED)
        baker.make(Schedule, end=end_1, status=SCHEDULE_STATUS_CHOICES.PUBLISHED)
        baker.make(Schedule, end=end_1, status=SCHEDULE_STATUS_CHOICES.PUBLISHED)
        baker.make(Schedule, end=end_1)
        baker.make(Schedule, end=end_1)
        baker.make(Schedule, end=end_1)


        with freeze_time("2020-01-01 09:00:00"):
            employee = baker.make(Employee, department=department, role=COMPANY_ROLE_CHOICES.EMPLOYEE)

        query = ScheduleQuerySet(employee)
        query.queryset_for_employee()

        self.assertQuerysetEqual(query.qs,
                                 [schedule_1.pk, schedule_2.pk, schedule_5.pk,schedule_6.pk],
                                 ordered=False,
                                 transform=attrgetter('pk'))
        _queryset_for_user_department.assert_called_once()


    @patch('schedule.query.ScheduleQuerySet.default_queryset')
    @patch('schedule.query.ScheduleQuerySet.queryset_for_manager_admin_or_manager')
    @patch('schedule.query.ScheduleQuerySet.queryset_for_staff')
    @patch('schedule.query.ScheduleQuerySet.queryset_for_employee')
    @patch('schedule.query.ScheduleQuerySet.queryset_sorting')
    def test_get_queryset(self, _queryset_sorting, _queryset_for_employee, _queryset_for_staff,
                          _queryset_for_manager_admin_or_manager, _default_queryset):

        schedule_1 = baker.make(Schedule, department=baker.make(Department))
        schedule_2 = baker.make(Schedule, department=baker.make(Department))
        schedule_3 = baker.make(Schedule, department=baker.make(Department))
        schedule_4 = baker.make(Schedule, department=baker.make(Department))

        query = ScheduleQuerySet(None)
        qs = query.get_queryset()

        self.assertQuerysetEqual(qs,
                                 [schedule_1.pk, schedule_2.pk, schedule_3.pk, schedule_4.pk],
                                 ordered=False,
                                 transform=attrgetter('pk'))

        _queryset_sorting.assert_called_once()
        _queryset_for_employee.assert_called_once()
        _queryset_for_staff.assert_called_once()
        _queryset_for_manager_admin_or_manager.assert_called_once()
        _default_queryset.assert_called_once()




    def test_default_queryset(self):
        company_1 = baker.make(Company)
        company_2 = baker.make(Company)


        user_1 = baker.make(Employee, department=baker.make(Department), company=company_1)
        user_2 = baker.make(Employee, department=baker.make(Department), company=company_2)

        schedule_1 = baker.make(Schedule, department=baker.make(Department, company=company_1))
        schedule_2 = baker.make(Schedule, department=baker.make(Department, company=company_1))
        schedule_3 = baker.make(Schedule, department=baker.make(Department, company=company_2))
        schedule_4 = baker.make(Schedule, department=baker.make(Department, company=company_2))

        query_1 = ScheduleQuerySet(user_1)
        query_2 = ScheduleQuerySet(user_2)

        query_1.default_queryset()
        query_2.default_queryset()

        self.assertQuerysetEqual(query_1.qs,
                                 [schedule_1.pk, schedule_2.pk],
                                 ordered=False,
                                 transform=attrgetter('pk'))
        self.assertQuerysetEqual(query_2.qs,
                                 [schedule_3.pk, schedule_4.pk],
                                 ordered=False,
                                 transform=attrgetter('pk'))

