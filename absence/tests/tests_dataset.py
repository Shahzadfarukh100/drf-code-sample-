import datetime as dt
from operator import attrgetter
from unittest.mock import call
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone
from django.utils.translation import ugettext as _
from django.utils.translation import ugettext_lazy as _
from freezegun import freeze_time
from model_bakery import baker

from absence.models import EmployeeAbsenceType, EmployeeAbsence, GeneralAbsence
from absence.modules.dataset_generator import EmployeeAbsenceListViewDataSetGenerator, \
    AbsenceTypeListViewDataSetGenerator, GeneralAbsenceListViewDataSetGenerator
from account.models import Employee, Department
from constants.db import DURATION, ABSENCE_STATUS_CHOICES, ABSENCE_ENTITLEMENT_PERIOD_CHOICE


class TestEmployeeAbsenceListViewDataSetGenerator(TestCase):

    @patch('absence.modules.dataset_generator.BaseDataSetGenerator.__init__')
    def test___init__(self, __init__):
        absence = baker.make(EmployeeAbsence)
        qs = EmployeeAbsence.objects.filter(id=absence.id)

        EmployeeAbsenceListViewDataSetGenerator(qs)

        __init__.assert_called_once()
        self.assertQuerysetEqual(__init__.call_args_list[0][0][0],
                                 [absence.pk],
                                 ordered=False,
                                 transform=attrgetter('pk'))

        self.assertEqual(__init__.call_args_list[0][1]['title'], 'employee_absence_list')

    @freeze_time("2020-01-01 09:00:00")
    @patch('absence.modules.dataset_generator.formatted_datetime')
    @patch('absence.modules.dataset_generator.local_datetime')
    @patch('absence.modules.dataset_generator.get_leave_end')
    @patch('absence.modules.dataset_generator.get_leave_start')
    @patch('absence.modules.dataset_generator.get_leaves_duration_string')
    def test_get_instance_data_row(self, _leaves_string, _leave_start, _leave_end, _local_datetime, _fm_datetime):
        submitted_for = baker.make(Employee, first_name='Jhon', last_name='A',
                                   department=baker.make(Department, name='Department For'))
        submitted_by = baker.make(Employee, first_name='Akram', last_name='A')
        submitted_to = baker.make(Employee, first_name='Ras', last_name='A')
        absence = baker.make(EmployeeAbsence, subject='Subject', submitted_for=submitted_for,
                             submitted_by=submitted_by, submitted_to=submitted_to,
                             absence_type=baker.make(EmployeeAbsenceType, name='AbsenceType')

                             )

        _leaves_string.return_value = 'Leave Duration'
        _leave_start.return_value = '05/01/2020'
        _leave_end.return_value = '06/01/2020'
        _local_datetime.return_value = timezone.make_aware(dt.datetime(2020, 1, 1, 12, 0, 0))
        _fm_datetime.return_value = '01/01/2020'

        res = EmployeeAbsenceListViewDataSetGenerator.get_instance_data_row(absence)
        expected = [
            'Akram A',
            'Jhon A',
            'Ras A',
            'Subject',
            '05/01/2020',
            '06/01/2020',
            'Leave Duration',
            str(ABSENCE_STATUS_CHOICES[ABSENCE_STATUS_CHOICES.PENDING]),
            'Department For',
            '01/01/2020',
            'AbsenceType'
        ]

        self.assertListEqual(res, expected)

        _leaves_string.assert_called_once_with(absence)
        _leave_start.assert_called_once_with(absence)
        _leave_end.assert_called_once_with(absence)
        _local_datetime.assert_called_once_with(timezone.make_aware(dt.datetime(2020, 1, 1, 9, 0, 0)))
        _fm_datetime.assert_called_once_with(timezone.make_aware(dt.datetime(2020, 1, 1, 12, 0, 0)))

    def test__get_header_row(self):
        header = EmployeeAbsenceListViewDataSetGenerator.get_header_row()

        self.assertListEqual(header, [
            _('SUBMITTED_BY'),
            _('SUBMITTED_FOR'),
            _('SUBMITTED_TO'),
            _('TITLE'),
            _('START'),
            _('END'),
            _('DURATION'),
            _('STATUS'),
            _('DEPARTMENT'),
            _('SUBMITTED_ON'),
            _('ABSENCE_TYPE'),
        ])


class TestAbsenceTypeListViewDataSetGenerator(TestCase):

    @patch('absence.modules.dataset_generator.BaseDataSetGenerator.__init__')
    def test___init__(self, __init__):
        absence_type = baker.make(EmployeeAbsenceType)
        qs = EmployeeAbsenceType.objects.filter(id=absence_type.id)

        AbsenceTypeListViewDataSetGenerator(qs)

        __init__.assert_called_once()
        self.assertQuerysetEqual(__init__.call_args_list[0][0][0],
                                 [absence_type.pk],
                                 ordered=False,
                                 transform=attrgetter('pk'))

        self.assertEqual(__init__.call_args_list[0][1]['title'], 'absence_type_list')

    def test__get_header_row(self):
        header = AbsenceTypeListViewDataSetGenerator.get_header_row()

        self.assertListEqual(header, [
            _('NAME'),
            _('DESCRIPTION'),
            _('ENTITLEMENT'),
            _('ABSENCE_PERIOD'),
            _('SUBMIT_BEFORE_DAYS'),
            _('PAID'),
            _('ABSENCE_DURATION'),
        ])

    def test_get_instance_data_row(self):
        absence_type = baker.make(EmployeeAbsenceType, name='Absence Type', description='Description', entitlement=15,
                                  period=ABSENCE_ENTITLEMENT_PERIOD_CHOICE.PER_MONTH, submit_before_days=5, paid=True,
                                  duration=DURATION.FULL_DAY
                                  )

        res = AbsenceTypeListViewDataSetGenerator.get_instance_data_row(absence_type)
        expected = [
            'Absence Type',
            'Description',
            15,
            _('PER_MONTH'),
            5,
            _('YES'),
            _('FULL_DAY')
        ]

        self.assertListEqual(res, expected)


class TestGeneralAbsenceListViewDataSetGenerator(TestCase):

    @patch('absence.modules.dataset_generator.BaseDataSetGenerator.__init__')
    def test___init__(self, __init__):
        general_absence = baker.make(GeneralAbsence)
        qs = GeneralAbsence.objects.filter(id=general_absence.id)

        GeneralAbsenceListViewDataSetGenerator(qs)

        __init__.assert_called_once()
        self.assertQuerysetEqual(__init__.call_args_list[0][0][0],
                                 [general_absence.pk],
                                 ordered=False,
                                 transform=attrgetter('pk'))

        self.assertEqual(__init__.call_args_list[0][1]['title'], 'general_absence_list')

    def test__get_header_row(self):
        header = GeneralAbsenceListViewDataSetGenerator.get_header_row()

        self.assertListEqual(header, [
            _('TITLE'),
            _('BODY'),
            _('STATUS'),
            _('SUBMITTED_BY'),
            _('START'),
            _('END'),
            _('DEPARTMENT')
        ])

    @patch('absence.modules.dataset_generator.formatted_date')
    @patch('absence.modules.dataset_generator.local_date')
    def test_get_instance_data_row(self, _local_date, _formatted_date):
        submitted_by = baker.make(Employee, first_name='Akram', last_name='A')

        general_absence = baker.make(GeneralAbsence, subject='Subject', body='Body',
                                     status=ABSENCE_STATUS_CHOICES.APPROVED, submitted_by=submitted_by,
                                     start=timezone.make_aware(dt.datetime(2020, 5, 1, 0, 0, 0)),
                                     end=timezone.make_aware(dt.datetime(2020, 5, 4, 0, 0, 0)))

        general_absence.department.add(baker.make(Department, name='Department 1'),
                                       baker.make(Department, name='Department 2'))

        _local_date.side_effect = [timezone.make_aware(dt.datetime(2020, 5, 1, 5, 0, 0)),
                                   timezone.make_aware(dt.datetime(2020, 5, 4, 5, 0, 0))]
        _formatted_date.side_effect = ['01/05/2020', '04/05/2020']

        res = GeneralAbsenceListViewDataSetGenerator.get_instance_data_row(general_absence)
        expected = [
            'Subject',
            'Body',
            _('APPROVED'),
            'Akram A',
            '01/05/2020',
            '04/05/2020',
            'Department 1, Department 2'
        ]

        self.assertListEqual(res, expected)

        self.assertEqual(_local_date.mock_calls,
                         [call(timezone.make_aware(dt.datetime(2020, 5, 1, 0, 0, 0))),
                          call(timezone.make_aware(dt.datetime(2020, 5, 4, 0, 0, 0)))])

        self.assertEqual(_formatted_date.mock_calls,
                         [call(timezone.make_aware(dt.datetime(2020, 5, 1, 5, 0, 0))),
                          call(timezone.make_aware(dt.datetime(2020, 5, 4, 5, 0, 0)))])
