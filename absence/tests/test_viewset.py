import datetime as dt
import random
from operator import attrgetter
from unittest.mock import patch, Mock

import time
from django.db.models import Q
from django.test import TestCase
from django.utils import timezone
from freezegun import freeze_time
from model_bakery import baker
from rest_framework import status

from absence.models import EmployeeAbsence, GeneralAbsence
from absence.models import EmployeeAbsenceType
from absence.viewsets.absence_type_viewset import EmployeeAbsenceTypeViewSet
from absence.viewsets.employee_absence_viewset import EmployeeAbsenceViewSet
from absence.viewsets.general_absence_viewset import GeneralAbsenceViewSet
from account.models import Employee, Department, Company
from account.tests.recipes import employee_recipe
from constants.db import COMPANY_ROLE_CHOICES, ABSENCE_STATUS_CHOICES, TODO_TYPE_CHOICES
from todo.models import Todo
from todo.utils import create_todos


class TestEmployeeAbsenceTypeViewSet(TestCase):

    def setUp(self):
        self.deleted_at = timezone.make_aware(dt.datetime(2020, 5, 2, 0, 0, 0))

        self.company_1 = baker.make(Company)
        self.company_2 = baker.make(Company)

        self.user_1 = baker.make(Employee, company=self.company_1)
        self.user_2 = baker.make(Employee, company=self.company_2)
        self.user_3 = baker.make(Employee)


        baker.make(EmployeeAbsenceType, company=self.company_1, name='ABC')
        baker.make(EmployeeAbsenceType, company=self.company_1, deleted_at=self.deleted_at, name='BCD')
        baker.make(EmployeeAbsenceType, company=self.company_1, name='CDE')
        baker.make(EmployeeAbsenceType, company=self.company_1, deleted_at=self.deleted_at, name='DEF')

        baker.make(EmployeeAbsenceType, company=self.company_2, name='ABC')
        baker.make(EmployeeAbsenceType, company=self.company_2, deleted_at=self.deleted_at, name='BCD')
        baker.make(EmployeeAbsenceType, company=self.company_2, name='CDE')
        baker.make(EmployeeAbsenceType, company=self.company_2, deleted_at=self.deleted_at, name='DEF')


        self.viewset = EmployeeAbsenceTypeViewSet()

    def test_get_all_queryset(self):
        with patch.object(self.viewset, 'get_request_user') as request_user:
            request_user.return_value = self.user_1
            res = self.viewset.get_all_queryset()
            self.assertQuerysetEqual(res,
                                     [('ABC', self.company_1, None), ('CDE', self.company_1, None)],
                                     transform=attrgetter('name', 'company', 'deleted_at'))

            request_user.return_value = self.user_2
            res = self.viewset.get_all_queryset()
            self.assertQuerysetEqual(res,
                                     [('ABC', self.company_2, None), ('CDE', self.company_2, None)],
                                     transform=attrgetter('name', 'company', 'deleted_at'))

            request_user.return_value = self.user_3
            res = self.viewset.get_all_queryset()
            self.assertQuerysetEqual(res,
                                     [],
                                     transform=attrgetter('name', 'company', 'deleted_at'))


    def test_get_inactive_queryset(self):
        with patch.object(self.viewset, 'get_request_user') as request_user:
            request_user.return_value = self.user_1
            res = self.viewset.get_inactive_queryset()
            self.assertQuerysetEqual(res,
                                     [('BCD', self.company_1, self.deleted_at), ('DEF', self.company_1, self.deleted_at)],
                                     transform=attrgetter('name', 'company', 'deleted_at'))

            request_user.return_value = self.user_2
            res = self.viewset.get_inactive_queryset()
            self.assertQuerysetEqual(res,
                                     [('BCD', self.company_2, self.deleted_at), ('DEF', self.company_2, self.deleted_at)],
                                     transform=attrgetter('name', 'company', 'deleted_at'))

            request_user.return_value = self.user_3
            res = self.viewset.get_inactive_queryset()
            self.assertQuerysetEqual(res,
                                     [],
                                     transform=attrgetter('name', 'company', 'deleted_at'))

    def test_get_restore_queryset(self):
        absence_types = EmployeeAbsenceType.objects.all()
        with patch.object(self.viewset, 'get_inactive_queryset') as inactive_queryset:
            inactive_queryset.return_value = absence_types
            res = self.viewset.get_restore_queryset()

            self.assertEqual(res, absence_types)
            inactive_queryset.assert_called_once()


    def test_get_export_archived_queryset(self):
        absence_types = EmployeeAbsenceType.objects.all()
        with patch.object(self.viewset, 'get_inactive_queryset') as inactive_queryset:
            inactive_queryset.return_value = absence_types
            res = self.viewset.get_export_archived_queryset()

            self.assertEqual(res, absence_types)
            inactive_queryset.assert_called_once()


    def test_get_export_archived_queryset(self):
        absence_types = EmployeeAbsenceType.objects.all()
        with patch.object(self.viewset, 'get_inactive_queryset') as inactive_queryset:
            inactive_queryset.return_value = absence_types
            res = self.viewset.get_export_archived_queryset()

            self.assertEqual(res, absence_types)
            inactive_queryset.assert_called_once()

    def test_get_archived_queryset(self):
        absence_types = EmployeeAbsenceType.objects.all()
        with patch.object(self.viewset, 'get_inactive_queryset') as inactive_queryset:
            inactive_queryset.return_value = absence_types
            res = self.viewset.get_archived_queryset()

            self.assertEqual(res, absence_types)
            inactive_queryset.assert_called_once()

    @freeze_time("2020-04-27 09:00:00")
    def test_perform_destroy(self):
        now = timezone.make_aware(dt.datetime(2020, 4, 27, 9, 0, 0))
        absence = baker.make(EmployeeAbsenceType)

        self.viewset.perform_destroy(absence)

        self.assertEqual(absence.deleted_at, now)

    @freeze_time("2020-04-27 09:00:00")
    def test_restore(self):
        now = timezone.make_aware(dt.datetime.now())
        absence = baker.make(EmployeeAbsenceType, deleted_at=now)

        with patch.object(self.viewset, 'get_object') as get_object:
            get_object.return_value = absence

            res =  self.viewset.restore()
            self.assertEqual(absence.deleted_at, None)

            self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_mark_todo_complete(self):
        company = baker.make(Company)
        user = baker.make(Employee, department=baker.make(Department), company=baker.make(Company))
        user_2 = baker.make(Employee, department=baker.make(Department), company=company)

        request = Mock()
        request.user = user

        todo_choices = [
            TODO_TYPE_CHOICES.TWO_FACTOR,
            TODO_TYPE_CHOICES.SYNC_CALENDAR,
            TODO_TYPE_CHOICES.UPDATE_LANGUAGE,
            TODO_TYPE_CHOICES.SET_PREFERENCES,
            TODO_TYPE_CHOICES.ACCEPT_TERMS,
            TODO_TYPE_CHOICES.CHECK_COMPANY_SETTINGS,
            TODO_TYPE_CHOICES.CHECK_DEPARTMENT_SETTINGS
        ]


        #
        # todo_1 = baker.make(Todo, source=company, type=TODO_TYPE_CHOICES.CHECK_ABSENCE_TYPES)
        # todo_2 = baker.make(Todo, source=baker.make(Company), type=TODO_TYPE_CHOICES.CHECK_ABSENCE_TYPES)
        # todo_3 = baker.make(Todo, source=company, type=random.choice(todo_choices))


        create_todos(type_=TODO_TYPE_CHOICES.CHECK_ABSENCE_TYPES, sources=[company])
        time.sleep(1)
        create_todos(type_=TODO_TYPE_CHOICES.CHECK_ABSENCE_TYPES, sources=[baker.make(Company)])
        time.sleep(1)
        create_todos(type_=random.choice(todo_choices), sources=[company])


        self.assertFalse(Todo.objects.all().order_by('created')[0].completed)
        self.assertFalse(Todo.objects.all().order_by('created')[1].completed)
        self.assertFalse(Todo.objects.all().order_by('created')[2].completed)

        self.viewset.mark_todo_complete(request)

        self.assertFalse(Todo.objects.all().order_by('created')[0].completed)
        self.assertFalse(Todo.objects.all().order_by('created')[1].completed)
        self.assertFalse(Todo.objects.all().order_by('created')[2].completed)

        request.user = user_2
        self.viewset.mark_todo_complete(request)

        self.assertTrue(Todo.objects.all().order_by('created')[0].completed)
        self.assertFalse(Todo.objects.all().order_by('created')[1].completed)
        self.assertFalse(Todo.objects.all().order_by('created')[2].completed)


class TestGeneralAbsenceViewSet(TestCase):

    def setUp(self):
        self.viewset = GeneralAbsenceViewSet()

    def test_get_all_queryset(self):
        absence_1 = baker.make(GeneralAbsence, deleted_at=None)
        absence_2 = baker.make(GeneralAbsence, deleted_at=None)
        absence_3 = baker.make(GeneralAbsence, deleted_at=timezone.make_aware(dt.datetime(2020, 4, 27, 9, 0, 0)))
        absence_4 = baker.make(GeneralAbsence, deleted_at=timezone.make_aware(dt.datetime(2020, 1, 1, 0, 0, 0)))

        qs = self.viewset.get_all_queryset()

        self.assertQuerysetEqual(qs,
                                 [absence_1.pk, absence_2.pk],
                                 ordered=False,
                                 transform=attrgetter('id'))

    def test_get_restore_queryset(self):
        absence_1 = baker.make(GeneralAbsence, deleted_at=None)
        absence_2 = baker.make(GeneralAbsence, deleted_at=None)
        absence_3 = baker.make(GeneralAbsence, deleted_at=timezone.make_aware(dt.datetime(2020, 4, 27, 9, 0, 0)))
        absence_4 = baker.make(GeneralAbsence, deleted_at=timezone.make_aware(dt.datetime(2020, 1, 1, 0, 0, 0)))

        qs = self.viewset.get_restore_queryset()

        self.assertQuerysetEqual(qs,
                                 [absence_3.pk, absence_4.pk],
                                 ordered=False,
                                 transform=attrgetter('id'))

    def test_get_archived_queryset(self):
        absence_1 = baker.make(GeneralAbsence, deleted_at=None)
        absence_2 = baker.make(GeneralAbsence, deleted_at=None)
        absence_3 = baker.make(GeneralAbsence, deleted_at=timezone.make_aware(dt.datetime(2020, 4, 27, 9, 0, 0)))
        absence_4 = baker.make(GeneralAbsence, deleted_at=timezone.make_aware(dt.datetime(2020, 1, 1, 0, 0, 0)))

        qs = self.viewset.get_archived_queryset()

        self.assertQuerysetEqual(qs,
                                 [absence_3.pk, absence_4.pk],
                                 ordered=False,
                                 transform=attrgetter('id'))

    def test_get_export_archived_queryset(self):
        absence_1 = baker.make(GeneralAbsence, deleted_at=None)
        absence_2 = baker.make(GeneralAbsence, deleted_at=None)
        absence_3 = baker.make(GeneralAbsence, deleted_at=timezone.make_aware(dt.datetime(2020, 4, 27, 9, 0, 0)))
        absence_4 = baker.make(GeneralAbsence, deleted_at=timezone.make_aware(dt.datetime(2020, 1, 1, 0, 0, 0)))

        qs = self.viewset.get_export_archived_queryset()

        self.assertQuerysetEqual(qs,
                                 [absence_3.pk, absence_4.pk],
                                 ordered=False,
                                 transform=attrgetter('id'))

    def test_filter_query(self):
        department = baker.make(Department)
        employee = employee_recipe.make()
        staff = employee_recipe.make(role=COMPANY_ROLE_CHOICES.STAFF)
        manager = employee_recipe.make(role=COMPANY_ROLE_CHOICES.MANAGER)
        manager_admin_1 = employee_recipe.make(role=COMPANY_ROLE_CHOICES.MANAGER_ADMIN)
        manager_admin_2 = employee_recipe.make(role=COMPANY_ROLE_CHOICES.MANAGER_ADMIN, active_department=department)

        with patch.object(self.viewset, 'get_request_user') as request_user:
            request_user.return_value = employee
            res = self.viewset.filter_query()
            expect = Q(company=employee.company, department=employee.department, status=ABSENCE_STATUS_CHOICES.APPROVED)
            self.assertEqual(res, expect)

        with patch.object(self.viewset, 'get_request_user') as request_user:
            request_user.return_value = staff
            res = self.viewset.filter_query()
            expect = Q(company=staff.company, department=staff.department)
            self.assertEqual(res, expect)

        with patch.object(self.viewset, 'get_request_user') as request_user:
            request_user.return_value = manager
            res = self.viewset.filter_query()
            expect = Q(company=manager.company)
            self.assertEqual(res, expect)

        with patch.object(self.viewset, 'get_request_user') as request_user:
            request_user.return_value = manager_admin_1
            res = self.viewset.filter_query()
            expect = Q(company=manager_admin_1.company)
            self.assertEqual(res, expect)

        with patch.object(self.viewset, 'get_request_user') as request_user:
            request_user.return_value = manager_admin_2
            res = self.viewset.filter_query()
            expect = Q(company=manager_admin_2.company, department=manager_admin_2.active_department)
            self.assertEqual(res, expect)

    @freeze_time("2020-04-27 09:00:00")
    def test_perform_destroy(self):
        absence = baker.make(GeneralAbsence)

        self.assertEqual(absence.deleted_at, None)

        self.viewset.perform_destroy(absence)

        self.assertEqual(GeneralAbsence.objects.get(id=absence.id).deleted_at,
                         timezone.make_aware(dt.datetime(2020, 4, 27, 9, 0, 0)))


class TestEmployeeAbsenceViewSet(TestCase):

    def setUp(self):
        start_1 = timezone.make_aware(dt.datetime(2020, 4, 27, 9, 0, 0))
        start_2 = timezone.make_aware(dt.datetime(2020, 5, 20, 0, 0, 0))
        start_3 = timezone.make_aware(dt.datetime(2020, 5, 27, 9, 0, 0))
        start_4 = timezone.make_aware(dt.datetime(2020, 5, 29, 9, 0, 0))

        self.company_1 = baker.make(Company)
        self.company_2 = baker.make(Company)

        self.user_1 = baker.make(Employee, company=self.company_1, role=COMPANY_ROLE_CHOICES.EMPLOYEE)
        self.user_2 = baker.make(Employee, company=self.company_2, role=COMPANY_ROLE_CHOICES.STAFF)
        self.user_3 = baker.make(Employee)

        baker.make(EmployeeAbsence, company=self.company_1, submitted_for=self.user_1, start=start_1, subject='ABCD')
        baker.make(EmployeeAbsence, company=self.company_1, submitted_for=self.user_1, submitted_to=self.user_1, start=start_2, subject='BCDE')
        baker.make(EmployeeAbsence, company=self.company_1, submitted_for=self.user_2, start=start_3, subject='CDEF')
        baker.make(EmployeeAbsence, company=self.company_1, submitted_for=self.user_2, submitted_to=self.user_2, start=start_4, subject='DEFG')

        baker.make(EmployeeAbsence, company=self.company_2, submitted_for=self.user_1, submitted_to=self.user_2, start=start_1, subject='ABCD')
        baker.make(EmployeeAbsence, company=self.company_2, submitted_for=self.user_1, start=start_2, subject='BCDE')
        baker.make(EmployeeAbsence, company=self.company_2, submitted_for=self.user_2, submitted_to=self.user_2, start=start_3, subject='CDEF')
        baker.make(EmployeeAbsence, company=self.company_2, submitted_for=self.user_2, start=start_4, subject='DEFG')

        baker.make(EmployeeAbsence)
        baker.make(EmployeeAbsence)
        baker.make(EmployeeAbsence)
        baker.make(EmployeeAbsence)

        self.viewset = EmployeeAbsenceViewSet()


    def test_get_all_queryset(self):
        with patch.object(self.viewset, 'get_request_user') as request_user:
            request_user.return_value = self.user_1
            res = self.viewset.get_all_queryset()
            self.assertQuerysetEqual(res,
                                     [('BCDE', self.company_1), ('ABCD', self.company_1)],
                                     transform=attrgetter('subject', 'company'))


            request_user.return_value = self.user_2
            res = self.viewset.get_all_queryset()
            self.assertQuerysetEqual(res,
                                     [('DEFG', self.company_2), ('CDEF', self.company_2), ('ABCD', self.company_2)],
                                     transform=attrgetter('subject', 'company'))


            request_user.return_value = self.user_3
            res = self.viewset.get_all_queryset()
            self.assertQuerysetEqual(res,
                                     [],
                                     transform=attrgetter('subject', 'company'))

