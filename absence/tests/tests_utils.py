from django.test import TestCase
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from model_bakery import baker

from absence.utils import *
from account.models import Company
from constants.db import ABSENCE_ENTITLEMENT_PERIOD_CHOICE


class TestUtils(TestCase):

    def test_get_leaves_duration(self):
        start = timezone.make_aware(dt.datetime(2020, 1, 1, 0, 0)).date()
        end = timezone.make_aware(dt.datetime(2020, 1, 2, 0, 0)).date()
        days = get_leaves_duration(start, end)
        self.assertEqual(days, 1)

        start = timezone.make_aware(dt.datetime(2020, 1, 5, 0, 0)).date()
        end = timezone.make_aware(dt.datetime(2020, 1, 10, 0, 0)).date()
        days = get_leaves_duration(start, end)
        self.assertEqual(days, 5)

    def test_can_be_notify(self):
        absence = baker.make(EmployeeAbsence, submitted_to=baker.make(Employee), submitted_for=baker.make(Employee))
        self.assertTrue(can_be_notify(absence))

        employee = baker.make(Employee)
        absence = baker.make(EmployeeAbsence, submitted_to=employee, submitted_for=employee)
        self.assertFalse(can_be_notify(absence))

    def test_get_leaves_duration_string(self):
        start = timezone.make_aware(dt.datetime(2020, 1, 5, 1, 1))
        end = timezone.make_aware(dt.datetime(2020, 1, 6, 2, 2))
        absence = baker.make(EmployeeAbsence,start=start, end=end)
        duration = get_leaves_duration_string(absence)
        self.assertEqual(duration, '1 ' + str(_('DAY')) + ' 1 ' + str(_('HOUR')) + ' 1 ' + str(_('MINUTE')))

        start = timezone.make_aware(dt.datetime(2020, 1, 5, 1, 1))
        end = timezone.make_aware(dt.datetime(2020, 1, 10, 5, 21))
        absence = baker.make(EmployeeAbsence, start=start, end=end)
        duration = get_leaves_duration_string(absence)
        self.assertEqual(duration, '5 ' + str(_('DAYS')) + ' 4 ' + str(_('HOURS')) + ' 20 ' + str(_('MINUTES')))

    def test_get_entitlement_overflow_interval_week(self):
        absence_type = baker.make(EmployeeAbsenceType, entitlement=2, period=ABSENCE_ENTITLEMENT_PERIOD_CHOICE.PER_WEEK)

        company = baker.make(Company)
        submitted_for = baker.make(Employee, company=company)

        start_1 = timezone.make_aware(dt.datetime(2020, 5, 12, 0, 0))
        end_1 = timezone.make_aware(dt.datetime(2020, 5, 15, 0, 0))
        absence_1 = baker.make(EmployeeAbsence, absence_type=absence_type, start=start_1, end=end_1,
                               company=company, status=ABSENCE_STATUS_CHOICES.APPROVED, submitted_for=submitted_for)
        res = get_entitlement_overflow_interval_week(absence_1)
        self.assertDictEqual(res, dict(start='2020-05-11', end='2020-05-17', consumed=0))

        start_2 = timezone.make_aware(dt.datetime(2020, 5, 19, 0, 0))
        end_2 = timezone.make_aware(dt.datetime(2020, 5, 21, 0, 0))
        absence_2 = baker.make(EmployeeAbsence, absence_type=absence_type, start=start_2, end=end_2,
                               company=company, status=ABSENCE_STATUS_CHOICES.APPROVED, submitted_for=submitted_for)
        res = get_entitlement_overflow_interval_week(absence_2)
        self.assertEqual(res, None)

        start_3 = timezone.make_aware(dt.datetime(2020, 5, 21, 0, 0))
        end_3 = timezone.make_aware(dt.datetime(2020, 5, 22, 0, 0))
        absence_3 = baker.make(EmployeeAbsence, absence_type=absence_type, start=start_3, end=end_3,
                               company=company, status=ABSENCE_STATUS_CHOICES.APPROVED, submitted_for=submitted_for)
        res = get_entitlement_overflow_interval_week(absence_3)
        self.assertEqual(res, dict(start='2020-05-18', end='2020-05-24', consumed=2))

        start_4 = timezone.make_aware(dt.datetime(2020, 5, 30, 0, 0))
        end_4 = timezone.make_aware(dt.datetime(2020, 6, 3, 0, 0))
        absence_4 = baker.make(EmployeeAbsence, absence_type=absence_type, start=start_4, end=end_4,
                               company=company, status=ABSENCE_STATUS_CHOICES.APPROVED, submitted_for=submitted_for)
        res = get_entitlement_overflow_interval_week(absence_4)
        self.assertEqual(res, None)
        
        
    def test_get_entitlement_overflow_interval_month(self):
        absence_type = baker.make(EmployeeAbsenceType, entitlement=5, period=ABSENCE_ENTITLEMENT_PERIOD_CHOICE.PER_MONTH)
        company = baker.make(Company)
        submitted_for = baker.make(Employee, company=company)


        start_1 = timezone.make_aware(dt.datetime(2020, 5, 12, 0, 0))
        end_1 = timezone.make_aware(dt.datetime(2020, 5, 15, 0, 0))
        absence_1 = baker.make(EmployeeAbsence, absence_type=absence_type, start=start_1, end=end_1,
                               company=company, status=ABSENCE_STATUS_CHOICES.APPROVED, submitted_for=submitted_for)
        res = get_entitlement_overflow_interval_month(absence_1)
        self.assertEqual(res, None)


        start_2 = timezone.make_aware(dt.datetime(2020, 5, 15, 0, 0))
        end_2 = timezone.make_aware(dt.datetime(2020, 5, 17, 0, 0))
        absence_2 = baker.make(EmployeeAbsence, absence_type=absence_type, start=start_2, end=end_2,
                               company=company, status=ABSENCE_STATUS_CHOICES.APPROVED, submitted_for=submitted_for)
        res = get_entitlement_overflow_interval_month(absence_2)
        self.assertEqual(res, None)


        start_3 = timezone.make_aware(dt.datetime(2020, 5, 18, 0, 0))
        end_3 = timezone.make_aware(dt.datetime(2020, 5, 20, 0, 0))
        absence_3 = baker.make(EmployeeAbsence, absence_type=absence_type, start=start_3, end=end_3,
                               company=company, status=ABSENCE_STATUS_CHOICES.APPROVED, submitted_for=submitted_for)
        res = get_entitlement_overflow_interval_month(absence_3)
        self.assertEqual(res, dict(start='2020-05-01', end='2020-05-31', consumed=5))


        start_4 = timezone.make_aware(dt.datetime(2020, 5, 30, 0, 0))
        end_4 = timezone.make_aware(dt.datetime(2020, 6, 20, 0, 0))
        absence_4 = baker.make(EmployeeAbsence, absence_type=absence_type, start=start_4, end=end_4,
                               company=company, status=ABSENCE_STATUS_CHOICES.APPROVED, submitted_for=submitted_for)
        res = get_entitlement_overflow_interval_month(absence_4)
        self.assertEqual(res, dict(start='2020-05-01', end='2020-05-31', consumed=7))


    def test_get_entitlement_overflow_interval_year(self):
        absence_type = baker.make(EmployeeAbsenceType, entitlement=18, period=ABSENCE_ENTITLEMENT_PERIOD_CHOICE.PER_YEAR)

        company = baker.make(Company)
        submitted_for = baker.make(Employee, company=company)


        start_1 = timezone.make_aware(dt.datetime(2020, 5, 10, 0, 0))
        end_1 = timezone.make_aware(dt.datetime(2020, 5, 25, 0, 0))
        absence_1 = baker.make(EmployeeAbsence, absence_type=absence_type, start=start_1, end=end_1,
                               company=company, status=ABSENCE_STATUS_CHOICES.APPROVED, submitted_for=submitted_for)
        res = get_entitlement_overflow_interval_year(absence_1)
        self.assertEqual(res, None)


        start_1 = timezone.make_aware(dt.datetime(2021, 5, 10, 0, 0))
        end_1 = timezone.make_aware(dt.datetime(2021, 5, 25, 0, 0))
        absence_1 = baker.make(EmployeeAbsence, absence_type=absence_type, start=start_1, end=end_1,
                               company=company, status=ABSENCE_STATUS_CHOICES.APPROVED, submitted_for=submitted_for)
        res = get_entitlement_overflow_interval_year(absence_1)
        self.assertEqual(res, None)


        start_1 = timezone.make_aware(dt.datetime(2020, 5, 25, 0, 0))
        end_1 = timezone.make_aware(dt.datetime(2020, 5, 31, 0, 0))
        absence_1 = baker.make(EmployeeAbsence, absence_type=absence_type, start=start_1, end=end_1,
                               company=company, status=ABSENCE_STATUS_CHOICES.APPROVED, submitted_for=submitted_for)
        res = get_entitlement_overflow_interval_year(absence_1)
        self.assertEqual(res, dict(start='2020-01-01', end='2020-12-31', consumed=15))

    def test_create_default_absence_types(self):
        company_1 = baker.make(Company)
        company_2 = baker.make(Company)

        create_default_absence_types(company_1)
        create_default_absence_types(company_2)

        self.assertEqual(6, EmployeeAbsenceType.objects.filter(company=company_1).count())
        self.assertEqual(6, EmployeeAbsenceType.objects.filter(company=company_2).count())
        self.assertEqual(12, EmployeeAbsenceType.objects.all().count())

