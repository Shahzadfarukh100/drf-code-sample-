import datetime as dt
import random
from unittest.mock import patch, Mock

from django.test import TestCase
from django.utils import timezone
from django.utils.translation import ugettext as _
from django.utils.translation import ugettext_lazy as _
from freezegun import freeze_time
from model_bakery import baker
from rest_framework.exceptions import ValidationError
from rest_framework.status import *

from absence.models import EmployeeAbsenceType, EmployeeAbsence, EmployeeAbsenceComment, GeneralAbsence
from absence.serializers.absence_type_serializer import EmployeeAbsenceTypeSerializer
from absence.serializers.employee_absence_serializer import EmployeeAbsenceCreateSerializer, \
    EmployeeAbsenceStatusUpdateSerializer, EmployeeAbsenceListSerializer
from absence.serializers.general_absence_serializer import GeneralAbsenceSerializer, GeneralAbsenceCreateSerializer, \
    GeneralAbsenceUpdateSerializer, GeneralAbsenceWriteBaseSerializer
from account.models import Employee, Department
from account.tests.recipes import staff_recipe, company_recipe, employee_recipe
from constants.db import COMPANY_ROLE_CHOICES, DURATION, ABSENCE_STATUS_CHOICES, ABSENCE_ENTITLEMENT_PERIOD_CHOICE


class TestEmployeeAbsenceCreateSerializer(TestCase):

    def setUp(self):
        self.maxDiff = None
        self.company = company_recipe.make()
        self.user = employee_recipe.make(company=self.company)
        self.staff = staff_recipe.make()
        self.serializer = EmployeeAbsenceCreateSerializer()


    def test_validate_dates(self):

        data = dict(start=timezone.make_aware(dt.datetime(2020, 5, 12)),
                    end=timezone.make_aware(dt.datetime(2020, 5, 12)))
        res = self.serializer.validate_dates(data)
        self.assertEqual(res, None)


        data = dict(start=timezone.make_aware(dt.datetime(2020, 5, 13)),
                    end=timezone.make_aware(dt.datetime(2020, 5, 12)))

        with self.assertRaises(ValidationError) as cm:
            self.serializer.validate_dates(data)
        self.assertEqual(cm.exception.status_code, HTTP_400_BAD_REQUEST)
        self.assertEqual(cm.exception.detail, [_('END_DATE_CAN_NOT_BE_A_DATE_BEFORE_START_DATE')])

    def test_set_end_date(self):
        data = dict(absence_type=baker.make(EmployeeAbsenceType),
                    end=timezone.make_aware(dt.datetime(2020, 5, 12)))
        self.serializer.set_end_date(data)
        self.assertEqual(data['end'], timezone.make_aware(dt.datetime(2020, 5, 13, 0, 0, 0)))

        data = dict(absence_type=baker.make(EmployeeAbsenceType, duration=DURATION.HOURLY),
                    end=timezone.make_aware(dt.datetime(2020, 5, 12, 12, 30, 0)))
        self.serializer.set_end_date(data)
        self.assertEqual(data['end'], timezone.make_aware(dt.datetime(2020, 5, 12, 12, 30, 0)))


    def test_set_employee_relations(self):
        user_1 = baker.make(Employee)
        with patch.object(self.serializer, 'get_request_user') as request_user:
            request_user.return_value = self.user

            data = dict(submitted_by='', submitted_to=user_1, submitted_for='')
            self.serializer.set_employee_relations(data)
            self.assertEqual(data['submitted_by'], self.user)
            self.assertEqual(data['submitted_for'], self.user)
            self.assertEqual(data['submitted_to'], user_1)


            data = dict(submitted_by='', submitted_to='', submitted_for=user_1)
            self.serializer.set_employee_relations(data)
            self.assertEqual(data['submitted_by'], self.user)
            self.assertEqual(data['submitted_for'], user_1)
            self.assertEqual(data['submitted_to'], self.user)

    @freeze_time("2020-04-27 09:00:00")
    def test_validate_submit_before(self):
        data = dict(absence_type=baker.make(EmployeeAbsenceType, submit_before_days=0),
                    start=timezone.make_aware(dt.datetime(2020, 5, 12)))
        res = self.serializer.validate_submit_before(data)
        self.assertEqual(res, None)

        data = dict(absence_type=baker.make(EmployeeAbsenceType, submit_before_days=1),
                    start=timezone.make_aware(dt.datetime(2020, 4, 27, 18, 0, 0)))
        with self.assertRaises(ValidationError) as cm:
            self.serializer.validate_submit_before(data)
        self.assertEqual(cm.exception.status_code, HTTP_400_BAD_REQUEST)
        self.assertEqual(cm.exception.detail, [_('ABSENCE_SHOULD_SUBMITTED_BEFORE_1_DAYS')])

        data = dict(absence_type=baker.make(EmployeeAbsenceType, submit_before_days=1),
                    start=timezone.make_aware(dt.datetime(2020, 4, 28, 10, 0, 0)))
        res = self.serializer.validate_submit_before(data)
        self.assertEqual(res, None)

        data = dict(absence_type=baker.make(EmployeeAbsenceType, submit_before_days=5),
                    start=timezone.make_aware(dt.datetime(2020, 4, 30, 18, 0, 0)))
        with self.assertRaises(ValidationError) as cm:
            self.serializer.validate_submit_before(data)
        self.assertEqual(cm.exception.status_code, HTTP_400_BAD_REQUEST)
        self.assertEqual(cm.exception.detail, [_('ABSENCE_SHOULD_SUBMITTED_BEFORE_5_DAYS')])

        data = dict(absence_type=baker.make(EmployeeAbsenceType, submit_before_days=5),
                    start=timezone.make_aware(dt.datetime(2020, 5, 2, 9, 0, 0)))
        res = self.serializer.validate_submit_before(data)
        self.assertEqual(res, None)

    def test_validate_overlap(self):
        start_1 = timezone.make_aware(dt.datetime(2020, 4, 30, 0, 0, 0))
        end_1 = timezone.make_aware(dt.datetime(2020, 5, 2, 0, 0, 0))

        err = _('ABSENCE_HAS_ALREADY_BEEN_APPLIED_IN_GIVEN_DATES_2020-04-30_TO_2020-05-01. '
                'PLEASE_CHOOSE_A_NON-OVERLAPPING_TIME_INTERVAL')
        err_hourly = _('ABSENCE_HAS_ALREADY_BEEN_APPLIED_IN_GIVEN_DATES_2020-04-30 00:00_TO_2020-05-02 00:00. '
                       'PLEASE_CHOOSE_A_NON-OVERLAPPING_TIME_INTERVAL')

        data = dict(start=start_1, end=end_1, submitted_for=self.user)
        res = self.serializer.validate_overlap(data)
        self.assertEqual(res, None)

        baker.make(EmployeeAbsence,
                   start=start_1,
                   end=end_1,
                   submitted_for=self.user,
                   company=self.company
                   )

        data = dict(start=start_1, end=end_1, submitted_for=self.user)
        with self.assertRaises(ValidationError) as cm:
            self.serializer.validate_overlap(data)
        self.assertEqual(cm.exception.status_code, HTTP_400_BAD_REQUEST)
        self.assertEqual(cm.exception.detail, [err])

        data = dict(start=timezone.make_aware(dt.datetime(2020, 5, 1, 0, 0, 0)),
                    end=timezone.make_aware(dt.datetime(2020, 5, 1, 0, 0, 0)),
                    submitted_for=self.user)
        with self.assertRaises(ValidationError) as cm:
            self.serializer.validate_overlap(data)
        self.assertEqual(cm.exception.status_code, HTTP_400_BAD_REQUEST)
        self.assertEqual(cm.exception.detail, [err])

        data = dict(start=timezone.make_aware(dt.datetime(2020, 4, 27, 0, 0, 0)),
                    end=timezone.make_aware(dt.datetime(2020, 5, 1, 0, 0, 0)),
                    submitted_for=self.user)
        with self.assertRaises(ValidationError) as cm:
            self.serializer.validate_overlap(data)
        self.assertEqual(cm.exception.status_code, HTTP_400_BAD_REQUEST)
        self.assertEqual(cm.exception.detail, [err])

        data = dict(start=timezone.make_aware(dt.datetime(2020, 5, 1, 0, 0, 0)),
                    end=timezone.make_aware(dt.datetime(2020, 5, 5, 0, 0, 0)),
                    submitted_for=self.user)
        with self.assertRaises(ValidationError) as cm:
            self.serializer.validate_overlap(data)
        self.assertEqual(cm.exception.status_code, HTTP_400_BAD_REQUEST)
        self.assertEqual(cm.exception.detail, [err])

        data = dict(start=timezone.make_aware(dt.datetime(2020, 4, 25, 0, 0, 0)),
                    end=timezone.make_aware(dt.datetime(2020, 5, 5, 0, 0, 0)),
                    submitted_for=self.user)
        with self.assertRaises(ValidationError) as cm:
            self.serializer.validate_overlap(data)
        self.assertEqual(cm.exception.status_code, HTTP_400_BAD_REQUEST)
        self.assertEqual(cm.exception.detail, [err])

        data = dict(start=timezone.make_aware(dt.datetime(2020, 4, 27, 0, 0, 0)),
                    end=start_1,
                    submitted_for=self.user)
        res = self.serializer.validate_overlap(data)
        self.assertEqual(res, None)

        data = dict(start=end_1,
                    end=timezone.make_aware(dt.datetime(2020, 5, 5, 0, 0, 0)),
                    submitted_for=self.user)
        res = self.serializer.validate_overlap(data)
        self.assertEqual(res, None)

        data = dict(start=timezone.make_aware(dt.datetime(2020, 5, 1, 0, 0, 0)),
                    end=timezone.make_aware(dt.datetime(2020, 5, 1, 0, 0, 0)),
                    submitted_for=self.user,
                    absence_duration=DURATION.HOURLY)
        with self.assertRaises(ValidationError) as cm:
            self.serializer.validate_overlap(data)
        self.assertEqual(cm.exception.status_code, HTTP_400_BAD_REQUEST)
        self.assertEqual(cm.exception.detail, [err_hourly])

    def test_validate_shift_overlap(self):
        start_1 = timezone.make_aware(dt.datetime(2020, 4, 30, 0, 0, 0))
        end_1 = timezone.make_aware(dt.datetime(2020, 5, 2, 0, 0, 0))

        with patch('absence.serializers.absence_base_serializer.is_employee_shift_exist_for_employee') as shift:
            data = dict(start=start_1, end=end_1, submitted_for=self.user, ignore_shift_overlap=True)
            res = self.serializer.validate_shift_overlap(data)
            self.assertEqual(res, None)
            shift.assert_not_called()

            shift.return_value = False
            data = dict(start=start_1, end=end_1, submitted_for=self.user, ignore_shift_overlap=True)
            res = self.serializer.validate_shift_overlap(data)
            self.assertEqual(res, None)
            shift.assert_not_called()

            data = dict(start=start_1, end=end_1, submitted_for=self.user, ignore_shift_overlap=False)
            shift.return_value = True
            with self.assertRaises(ValidationError) as cm:
                self.serializer.validate_shift_overlap(data)
            self.assertEqual(cm.exception.status_code, HTTP_400_BAD_REQUEST)

            expected_error = {'ignore_shift_overlap': _(
                'EMPLOYEE_SHIFT_EXIST_FOR_THIS_DURATION.ARE_YOU_STILL_WANT_TO_SUBMIT_ABSENCE')}
            self.assertEqual(cm.exception.detail, expected_error)
            shift.assert_called_once_with(self.user, start_1, end_1)

            shift.return_value = False
            data = dict(start=start_1, end=end_1, submitted_for=self.user, ignore_shift_overlap=False)
            res = self.serializer.validate_shift_overlap(data)
            self.assertEqual(res, None)


    def test_set_status(self):
        with patch.object(self.serializer, 'get_request_user') as request_user:
            request_user.return_value = self.user
            data = dict(status=1)
            self.serializer.set_status(data)
            self.assertEqual(data['status'], ABSENCE_STATUS_CHOICES.PENDING)


            request_user.return_value = self.staff
            data = dict(submitted_to=self.user, status=1, submitted_by=self.user)
            self.serializer.set_status(data)
            self.assertEqual(data['status'], ABSENCE_STATUS_CHOICES.APPROVED)

    def test_set_company(self):
        data = dict(company='', submitted_for=self.user)
        self.serializer.set_company(data)
        self.assertEqual(data['company'], self.company)

    def test_validate_submitted_to(self):
        user_1 = baker.make(Employee, role=COMPANY_ROLE_CHOICES.EMPLOYEE)
        with patch.object(self.serializer, 'get_request_user') as request_user:
            request_user.return_value = self.user

            with self.assertRaises(ValidationError) as cm:
                self.serializer.validate_submitted_to(user_1)
            self.assertEqual(cm.exception.status_code, HTTP_400_BAD_REQUEST)
            self.assertEqual(cm.exception.detail, [_('EMPLOYEE_TO_SUBMIT_ABSENCE_NOT_FOUND')])

            res = self.serializer.validate_submitted_to(self.staff)
            self.assertEqual(res, self.staff)

    def test_get_request_user(self):
        request = Mock()
        request.user = self.user
        context = dict(request=request)

        serializer = EmployeeAbsenceCreateSerializer(instance=self.user, context=context)
        res = serializer.get_request_user()
        self.assertEqual(res, self.user)


    def test_validate(self):
        with patch.object(self.serializer, 'validate_dates') as v_dates:
            with patch.object(self.serializer, 'set_end_date') as end_date:
                with patch.object(self.serializer, 'set_employee_relations') as em:
                    with patch.object(self.serializer, 'validate_submit_before') as before:
                        with patch.object(self.serializer, 'validate_overlap') as overlap:
                            with patch.object(self.serializer, 'validate_shift_overlap') as s_overlap:
                                with patch.object(self.serializer, 'set_status') as status:
                                    with patch.object(self.serializer, 'set_company') as company:

                                        data = dict()
                                        self.serializer.validate(data)
                                        v_dates.assert_called_once_with(data)
                                        end_date.assert_called_once_with(data)
                                        em.assert_called_once_with(data)
                                        before.assert_called_once_with(data)
                                        overlap.assert_called_once_with(data)
                                        s_overlap.assert_called_once_with(data)
                                        status.assert_called_once_with(data)
                                        company.assert_called_once_with(data)

    @freeze_time("2020-04-27 09:00:00")
    def test_create(self):
        submitted_to = baker.make(Employee)
        start = timezone.make_aware(dt.datetime(2020, 5, 1, 0, 0, 0))
        end = timezone.make_aware(dt.datetime(2020, 5, 5, 0, 0, 0))
        absence_type = baker.make(EmployeeAbsenceType)
        data = dict(subject='Test Absence', submitted_for=self.user,
                    submitted_by=self.user, submitted_to=submitted_to, start=start, end=end,
                    absence_type=absence_type, comment='Test Absence Comment', company=self.user.company,
                    ignore_shift_overlap=True, absence_duration=DURATION.FULL_DAY)

        with patch.object(self.serializer, 'get_request_user') as request_user:
            request_user.return_value = self.user
            with patch('absence.serializers.employee_absence_serializer.absence_created') as absence_created:
                self.serializer.create(data)

                self.assertEqual(1, EmployeeAbsence.objects.count())
                self.assertEqual('Test Absence', EmployeeAbsence.objects.first().subject)
                self.assertEqual(start, EmployeeAbsence.objects.first().start)
                self.assertEqual(end, EmployeeAbsence.objects.first().end)
                self.assertEqual(submitted_to, EmployeeAbsence.objects.first().submitted_to)
                self.assertEqual(self.user, EmployeeAbsence.objects.first().submitted_for)
                self.assertEqual(self.user, EmployeeAbsence.objects.first().submitted_by)

                self.assertEqual(1, EmployeeAbsenceComment.objects.count())
                self.assertEqual('Test Absence Comment', EmployeeAbsenceComment.objects.first().comment)
                self.assertEqual(self.user, EmployeeAbsenceComment.objects.first().commented_by)
                absence_created.send.assert_called_once()


class TestEmployeeAbsenceStatusUpdateSerializer(TestCase):

    def setUp(self):
        self.company = company_recipe.make()
        self.user = employee_recipe.make(company=self.company)
        self.staff = staff_recipe.make()
        self.absence = baker.make(EmployeeAbsence, end=timezone.make_aware(dt.datetime(2020, 5, 2, 0, 0, 0)),
                                  submitted_for=self.user)
        self.serializer = EmployeeAbsenceStatusUpdateSerializer(instance=self.absence)

    @patch('absence.serializers.employee_absence_serializer.is_employee_shift_exist_for_employee', return_value=True)
    def test_validate_shift_overlap(self, shift):
        shift.return_value = False

        data = dict(ignore_shift_overlap=False, status=ABSENCE_STATUS_CHOICES.PENDING)
        res = self.serializer.validate_shift_overlap(data)
        self.assertEqual(res, None)

        data = dict(ignore_shift_overlap=True, status=ABSENCE_STATUS_CHOICES.APPROVED)
        res = self.serializer.validate_shift_overlap(data)
        self.assertEqual(res, None)

        data = dict(ignore_shift_overlap=True, status=ABSENCE_STATUS_CHOICES.APPROVED)
        res = self.serializer.validate_shift_overlap(data)
        self.assertEqual(res, None)

        shift.return_value = True
        data = dict(ignore_shift_overlap=False, status=ABSENCE_STATUS_CHOICES.APPROVED,
                    start=self.absence.start, end=self.absence.end,
                    submitted_for=self.user)
        with self.assertRaises(ValidationError) as cm:
            self.serializer.validate_shift_overlap(data)
        self.assertEqual(cm.exception.status_code, HTTP_400_BAD_REQUEST)
        self.assertEqual(cm.exception.detail, {'ignore_shift_overlap':
                                                   _(
                                                       'EMPLOYEE_SHIFT_EXIST_FOR_THIS_DURATION.ARE_YOU_STILL_WANT_TO_APPROVE_ABSENCE')})
        shift.assert_called_once_with(self.user, self.absence.start, self.absence.end)

    def test_validate(self):
        data = dict()
        with patch.object(self.serializer, 'validate_shift_overlap') as validate_shift_overlap:
            with patch.object(self.serializer, 'validate_balance') as validate_balance:
                res = self.serializer.validate(data)
                self.assertDictEqual(res, data)

                validate_shift_overlap.assert_called_once_with(data)
                validate_balance.assert_called_once_with(data)

    def test_validate_balance(self):
        with patch.object(self.serializer, 'validate_balance_per_week') as validate_balance_per_week:
            absence_type = baker.make(EmployeeAbsenceType, entitlement=10,
                                      period=ABSENCE_ENTITLEMENT_PERIOD_CHOICE.PER_WEEK)
            absence = baker.make(EmployeeAbsence, status=ABSENCE_STATUS_CHOICES.APPROVED, absence_type=absence_type)

            self.serializer.instance = absence
            data = dict(status=ABSENCE_STATUS_CHOICES.APPROVED)

            self.serializer.validate_balance(data)

            validate_balance_per_week.assert_called_once()

        with patch.object(self.serializer, 'validate_balance_per_month') as validate_balance_per_month:
            absence_type = baker.make(EmployeeAbsenceType, entitlement=10,
                                      period=ABSENCE_ENTITLEMENT_PERIOD_CHOICE.PER_MONTH)
            absence = baker.make(EmployeeAbsence, status=ABSENCE_STATUS_CHOICES.APPROVED, absence_type=absence_type)

            self.serializer.instance = absence
            data = dict(status=ABSENCE_STATUS_CHOICES.APPROVED)

            self.serializer.validate_balance(data)

            validate_balance_per_month.assert_called_once()

        with patch.object(self.serializer, 'validate_balance_per_year') as validate_balance_per_year:
            absence_type = baker.make(EmployeeAbsenceType, entitlement=10,
                                      period=ABSENCE_ENTITLEMENT_PERIOD_CHOICE.PER_YEAR)
            absence = baker.make(EmployeeAbsence, status=ABSENCE_STATUS_CHOICES.APPROVED, absence_type=absence_type)

            self.serializer.instance = absence
            data = dict(status=ABSENCE_STATUS_CHOICES.APPROVED)

            self.serializer.validate_balance(data)

            validate_balance_per_year.assert_called_once()

    def test_validate_balance_per_week(self):
        absence_type = baker.make(EmployeeAbsenceType, entitlement=2)
        absence = baker.make(EmployeeAbsence, absence_type=absence_type)
        self.serializer.instance = absence
        with patch('absence.serializers.employee_absence_serializer.get_entitlement_overflow_interval_week') as e_w:
            e_w.return_value = dict(consumed=5, start='17/05/2020', end='21/05/2020')

            with self.assertRaises(ValidationError) as cm:
                self.serializer.validate_balance_per_week()
            self.assertEqual(cm.exception.status_code, HTTP_400_BAD_REQUEST)

            expected_error = [_(
                'ALREADY_HAVE_AVAILED_5_ABSENCES_FOR_WEEK_FROM_17/05/2020_TO_21/05/2020.MAXIMUM_ENTITLEMENT_FOR_THIS_WEEK_IS_2')]
            self.assertEqual(cm.exception.detail, expected_error)

            e_w.assert_called_once_with(absence)

    def test_validate_balance_per_month(self):
        absence_type = baker.make(EmployeeAbsenceType, entitlement=10)
        absence = baker.make(EmployeeAbsence, absence_type=absence_type)
        self.serializer.instance = absence
        with patch('absence.serializers.employee_absence_serializer.get_entitlement_overflow_interval_month') as e_m:
            e_m.return_value = dict(consumed=5, start='17/05/2020', end='21/05/2020')

            with self.assertRaises(ValidationError) as cm:
                self.serializer.validate_balance_per_month()
            self.assertEqual(cm.exception.status_code, HTTP_400_BAD_REQUEST)

            expected_error = [_(
                'ALREADY_HAVE_AVAILED_5_ABSENCES_FOR_MONTH_FROM_17/05/2020_TO_21/05/2020.MAXIMUM_ENTITLEMENT_FOR_THIS_MONTH_IS_10')]
            self.assertEqual(cm.exception.detail, expected_error)

            e_m.assert_called_once_with(absence)

    def test_validate_balance_per_year(self):
        absence_type = baker.make(EmployeeAbsenceType, entitlement=18)
        absence = baker.make(EmployeeAbsence, absence_type=absence_type)
        self.serializer.instance = absence
        with patch('absence.serializers.employee_absence_serializer.get_entitlement_overflow_interval_year') as e_y:
            e_y.return_value = dict(consumed=5, start='17/05/2020', end='21/05/2020')

            with self.assertRaises(ValidationError) as cm:
                self.serializer.validate_balance_per_year()
            self.assertEqual(cm.exception.status_code, HTTP_400_BAD_REQUEST)

            expected_error = [_(
                'ALREADY_HAVE_AVAILED_5_ABSENCES_FOR_YEAR_FROM_17/05/2020_TO_21/05/2020.MAXIMUM_ENTITLEMENT_FOR_THIS_YEAR_IS_18')]
            self.assertEqual(cm.exception.detail, expected_error)

            e_y.assert_called_once_with(absence)

    def test_update(self):
        comment = baker.make(EmployeeAbsenceComment)
        absence = baker.make(EmployeeAbsence, status=ABSENCE_STATUS_CHOICES.PENDING)


        with patch.object(self.serializer, 'create_comment') as create_comment:
            with patch.object(self.serializer, 'send_notifications') as send_notifications:
                create_comment.return_value = comment
                data = dict(status=ABSENCE_STATUS_CHOICES.PENDING)
                res = self.serializer.update(absence, data)

                self.assertEqual(res, absence)
                send_notifications.assert_not_called()
                create_comment.assert_called_once_with(data)


        with patch.object(self.serializer, 'create_comment') as create_comment:
            with patch.object(self.serializer, 'send_notifications') as send_notifications:
                create_comment.return_value = comment
                data = dict(status=ABSENCE_STATUS_CHOICES.REJECTED)
                res = self.serializer.update(absence, data)

                self.assertEqual(res, absence)
                send_notifications.assert_called_once_with(comment)
                create_comment.assert_called_once_with(data)




class TestEmployeeAbsenceTypeSerializer(TestCase):
    def setUp(self):
        self.company = company_recipe.make()
        self.user = employee_recipe.make(company=self.company)
        self.other_company = company_recipe.make()
        self.other_user = employee_recipe.make(company=self.other_company)
        request = Mock()
        request.user = self.user
        context = dict(request=request)
        self.serializer = EmployeeAbsenceTypeSerializer(context=context)

    def test_validate_name(self):
        baker.make(EmployeeAbsenceType, company=self.company, deleted_at=None, name='Absence Type 1')
        with self.assertRaises(ValidationError) as cm:
            self.serializer.validate_name('Absence Type 1')
        self.assertEqual(cm.exception.status_code, HTTP_400_BAD_REQUEST)
        self.assertEqual(cm.exception.detail, [_('ABSENCE_TYPE_ALREADY_EXISTS')])

        baker.make(EmployeeAbsenceType, company=self.company, deleted_at=timezone.make_aware(dt.datetime(2020, 2, 1)),
                   name='Absence Type 2')
        with self.assertRaises(ValidationError) as cm:
            self.serializer.validate_name('Absence Type 2')
        self.assertEqual(cm.exception.status_code, HTTP_400_BAD_REQUEST)
        self.assertEqual(cm.exception.detail,
                         [_('ABSENCE_TYPE_WITH_THE_GIVEN_NAME_HAS_BEEN_ARCHIVED_RESTORE_IT_OR_TRY_WITH_ANOTHER_NAME')])


        request = Mock()
        request.user = self.other_user
        context = dict(request=request)
        serializer = EmployeeAbsenceTypeSerializer(context=context)
        res = serializer.validate_name('Absence Type 1')
        self.assertEqual(res, 'Absence Type 1')

    def test_validate(self):
        with patch.object(self.serializer, 'get_request_user') as request_user:
            request_user.return_value = self.user
            res = self.serializer.validate(dict())
            self.assertDictEqual(res, dict(company=self.company))


class TestEmployeeAbsenceListSerializer(TestCase):

    @patch('absence.serializers.employee_absence_serializer.get_leaves_duration_string')
    def test_get_duration(self, duration):
        absence = baker.make(EmployeeAbsence)
        EmployeeAbsenceListSerializer.get_duration(absence)
        duration.assert_called_once_with(absence)


class TestGeneralAbsenceWriteBaseSerializer(TestCase):
    def setUp(self):
        self.maxDiff = None
        self.company = company_recipe.make()
        self.user = employee_recipe.make(company=self.company)
        self.staff = staff_recipe.make()
        self.serializer = GeneralAbsenceWriteBaseSerializer()

    def test_add_departments(self):
        departments = [baker.make(Department), baker.make(Department), baker.make(Department), baker.make(Department)]
        absence = baker.make(GeneralAbsence)
        self.serializer.add_departments(absence, departments)

        self.assertListEqual(departments, list(absence.department.all()))
        self.assertEqual(4, absence.department.count())

    def test_remove_departments(self):
        department_1 = baker.make(Department)
        department_2 = baker.make(Department)
        department_3 = baker.make(Department)
        absence = baker.make(GeneralAbsence)

        absence.department.add(department_1)
        absence.department.add(department_2)
        absence.department.add(department_3)

        self.serializer.remove_departments(absence, [department_1, department_3])

        self.assertListEqual([department_2], list(absence.department.all()))
        self.assertEqual(1, absence.department.count())


    @freeze_time("2020-04-27 09:00:00")
    def test_validate(self):
        start = timezone.make_aware(dt.datetime(2020, 5, 5, 0, 0, 0))
        end = timezone.make_aware(dt.datetime(2020, 5, 4, 0, 0, 0))
        data = dict(start=start, end=end)
        with self.assertRaises(ValidationError) as cm:
            self.serializer.validate(data)
        self.assertEqual(cm.exception.status_code, HTTP_400_BAD_REQUEST)
        self.assertEqual(cm.exception.detail, [_('END_DATE_CAN_NOT_BE_A_DATE_BEFORE_START_DATE')])


        start = timezone.make_aware(dt.datetime(2020, 5, 5, 0, 0, 0))
        end = timezone.make_aware(dt.datetime(2020, 5, 5, 0, 0, 0))
        data = dict(start=start, end=end)
        res = self.serializer.validate(data)
        self.assertDictEqual(res, data)


class TestGeneralAbsenceSerializer(TestCase):
    def setUp(self):
        self.maxDiff = None
        self.company = company_recipe.make()
        self.user = employee_recipe.make(company=self.company)
        self.staff = staff_recipe.make()
        self.serializer = GeneralAbsenceSerializer()

    @freeze_time("2020-04-27 09:00:00")
    def test_get_duration(self):
        start = timezone.make_aware(dt.datetime(2020, 5, 1, 0, 0, 0))
        end = timezone.make_aware(dt.datetime(2020, 5, 5, 0, 0, 0))
        absence = baker.make(GeneralAbsence, start=start, end=end)
        res = self.serializer.get_duration(absence)
        self.assertEqual(res, '4 ' + str(_('DAYS')))

        start = timezone.make_aware(dt.datetime(2020, 5, 1, 0, 0, 0))
        end = timezone.make_aware(dt.datetime(2020, 5, 2, 0, 0, 0))
        absence = baker.make(GeneralAbsence, start=start, end=end)
        res = self.serializer.get_duration(absence)
        self.assertEqual(res, '1 '+str(_('DAY')))

    def test_get_request_user(self):
        request = Mock()
        request.user = self.user
        context = dict(request=request)
        serializer = GeneralAbsenceSerializer(instance=self.user, context=context)
        res = serializer.get_request_user()
        self.assertEqual(res, self.user)

    @patch('absence.serializers.general_absence_serializer.can_general_absence_update')
    def test_get_can_update(self, _can_general_absence_update):

        absence = baker.make(GeneralAbsence)
        with patch.object(self.serializer, 'get_request_user') as get_request_user:
            random_bool = random.choice([True, False])
            get_request_user.return_value = self.user
            _can_general_absence_update.return_value = random_bool

            self.assertEqual(self.serializer.get_can_update(absence), random_bool)

            get_request_user.assert_called_once()
            _can_general_absence_update.assert_called_once_with(self.user, absence)


    @patch('absence.serializers.general_absence_serializer.can_general_absence_delete')
    def test_get_can_delete(self, _can_general_absence_delete):

        absence = baker.make(GeneralAbsence)
        with patch.object(self.serializer, 'get_request_user') as get_request_user:
            random_bool = random.choice([True, False])
            get_request_user.return_value = self.user
            _can_general_absence_delete.return_value = random_bool

            self.assertEqual(self.serializer.get_can_delete(absence), random_bool)

            get_request_user.assert_called_once()
            _can_general_absence_delete.assert_called_once_with(self.user, absence)



    @patch('absence.serializers.general_absence_serializer.can_general_absence_restore')
    def test_get_can_restore(self, _can_general_absence_restore):

        absence = baker.make(GeneralAbsence)
        with patch.object(self.serializer, 'get_request_user') as get_request_user:
            random_bool = random.choice([True, False])
            get_request_user.return_value = self.user
            _can_general_absence_restore.return_value = random_bool

            self.assertEqual(self.serializer.get_can_restore(absence), random_bool)

            get_request_user.assert_called_once()
            _can_general_absence_restore.assert_called_once_with(self.user, absence)




class TestGeneralAbsenceCreateSerializer(TestCase):
    def setUp(self):
        self.maxDiff = None
        self.company = company_recipe.make()
        self.user = employee_recipe.make(company=self.company)
        self.staff = staff_recipe.make()
        self.serializer = GeneralAbsenceCreateSerializer()

    @freeze_time("2020-04-27 09:00:00")
    def test_create(self):
        start = timezone.make_aware(dt.datetime(2020, 5, 4, 0, 0, 0))
        end = timezone.make_aware(dt.datetime(2020, 5, 5, 0, 0, 0))
        departments = [baker.make(Department), baker.make(Department), baker.make(Department), baker.make(Department)]

        data = dict(subject='Test Absence', body='Test Absence Body', start=start, end=end,
                    status=ABSENCE_STATUS_CHOICES.APPROVED, department=departments)

        with patch.object(self.serializer, 'get_request_user') as request_user:
            request_user.return_value = self.user
            with patch.object(self.serializer, 'get_departments') as get_departments:
                with patch.object(self.serializer, 'add_departments') as add_departments:
                    with patch('absence.serializers.general_absence_serializer.general_absence_created') as absence_created:
                        get_departments.return_value = [1, 2, 3]

                        res = self.serializer.create(data)

                        self.assertEqual(1, GeneralAbsence.objects.count())
                        self.assertEqual(res, GeneralAbsence.objects.first())
                        self.assertEqual(self.user, GeneralAbsence.objects.first().submitted_by)
                        self.assertEqual(self.user.company, GeneralAbsence.objects.first().company)
                        self.assertEqual(start, GeneralAbsence.objects.first().start)
                        self.assertEqual(end + dt.timedelta(days=1), GeneralAbsence.objects.first().end)

                        request_user.assert_called_once()
                        absence_created.send.assert_called_once()
                        add_departments.assert_called_once_with(res, [1, 2, 3])
                        get_departments.assert_called_once_with(data)


    def test_get_departments(self):

        department_1 = baker.make(Department)
        department_2 = baker.make(Department)
        department_3 = baker.make(Department)
        department_4 = baker.make(Department)

        manager = baker.make(Employee, department=department_1,
                             role=random.choice([COMPANY_ROLE_CHOICES.MANAGER_ADMIN, COMPANY_ROLE_CHOICES.MANAGER]))


        staff = baker.make(Employee, department=department_2, role=COMPANY_ROLE_CHOICES.STAFF)

        with patch.object(self.serializer, 'get_request_user') as request_user:
            request_user.return_value = manager

            data = dict(department=[str(department_1.pk), str(department_1.pk), str(department_3.pk), str(department_4.pk)])

            res = self.serializer.get_departments(data)

            self.assertListEqual(res, [str(department_1.pk), str(department_1.pk), str(department_3.pk), str(department_4.pk)])
            self.assertDictEqual(data, {})

        with patch.object(self.serializer, 'get_request_user') as request_user:
            request_user.return_value = staff

            data = dict(department=[str(department_1.pk), str(department_1.pk), str(department_3.pk), str(department_4.pk)])

            res = self.serializer.get_departments(data)

            self.assertListEqual(res, [department_2])
            self.assertDictEqual(data, {})




class TestGeneralAbsenceUpdateSerializer(TestCase):
    def setUp(self):
        self.maxDiff = None
        self.company = company_recipe.make()
        self.user = employee_recipe.make(company=self.company)
        self.staff = staff_recipe.make()
        self.serializer = GeneralAbsenceUpdateSerializer()

    @freeze_time("2020-04-27 09:00:00")
    def test_update(self):
        start = timezone.make_aware(dt.datetime(2020, 5, 4, 0, 0, 0))
        end = timezone.make_aware(dt.datetime(2020, 5, 5, 0, 0, 0))

        department_1 = baker.make(Department)
        department_2 = baker.make(Department)
        department_3 = baker.make(Department)
        absence = baker.make(GeneralAbsence, submitted_by=self.user, company=self.company)

        absence.department.add(department_1)
        absence.department.add(department_3)

        data = dict(subject='Test Absence', body='Test Absence Body', start=start, end=end,
                    status=ABSENCE_STATUS_CHOICES.APPROVED, department=[str(department_1.pk), str(department_2.pk)])


        with patch.object(self.serializer, 'get_departments') as get_departments:
            with patch.object(self.serializer, 'add_departments') as add_departments:
                with patch.object(self.serializer, 'remove_departments') as remove_departments:
                    get_departments.return_value = [1, 2, 3]

                    res = self.serializer.update(absence, data)

                    self.assertEqual(1, GeneralAbsence.objects.count())
                    self.assertEqual(res, GeneralAbsence.objects.first())
                    self.assertEqual(self.user, GeneralAbsence.objects.first().submitted_by)
                    self.assertEqual(self.company, GeneralAbsence.objects.first().company)
                    self.assertEqual(start, GeneralAbsence.objects.first().start)
                    self.assertEqual(end + dt.timedelta(days=1), GeneralAbsence.objects.first().end)

                    get_departments.assert_called_once_with(absence, data)
                    add_departments.assert_called_once()
                    remove_departments.assert_called_once()


    def test_get_departments(self):



        department_1 = baker.make(Department)
        department_2 = baker.make(Department)
        department_3 = baker.make(Department)
        department_4 = baker.make(Department)

        absence_1 = baker.make(GeneralAbsence, submitted_by=baker.make(Employee, department=department_1, role=COMPANY_ROLE_CHOICES.STAFF))
        absence_2 = baker.make(GeneralAbsence,
                               submitted_by=baker.make(Employee, department=baker.make(Department),
                                                       role=random.choice([COMPANY_ROLE_CHOICES.MANAGER_ADMIN,
                                                                           COMPANY_ROLE_CHOICES.MANAGER])))

        manager = baker.make(Employee, department=department_1,
                             role=random.choice([COMPANY_ROLE_CHOICES.MANAGER_ADMIN, COMPANY_ROLE_CHOICES.MANAGER]))


        staff = baker.make(Employee, department=department_2, role=COMPANY_ROLE_CHOICES.STAFF)

        with patch.object(self.serializer, 'get_request_user') as request_user:
            request_user.return_value = random.choice([staff, manager])

            data = dict(department=[str(department_1.pk), str(department_1.pk), str(department_3.pk), str(department_4.pk)])

            res = self.serializer.get_departments(absence_1, data)

            self.assertListEqual(res, [str(department_1.pk)])
            self.assertDictEqual(data, {})


        with patch.object(self.serializer, 'get_request_user') as request_user:
            request_user.return_value = manager

            data = dict(department=[str(department_1.pk), str(department_1.pk), str(department_3.pk), str(department_4.pk)])

            res = self.serializer.get_departments(absence_2, data)

            self.assertListEqual(res, [str(department_1.pk), str(department_1.pk), str(department_3.pk), str(department_4.pk)])
            self.assertDictEqual(data, {})

        with patch.object(self.serializer, 'get_request_user') as request_user:
            request_user.return_value = staff

            data = dict(department=[str(department_1.pk), str(department_1.pk), str(department_3.pk), str(department_4.pk)])

            res = self.serializer.get_departments(absence_2, data)

            self.assertListEqual(res, [str(department_2.pk)])
            self.assertDictEqual(data, {})
