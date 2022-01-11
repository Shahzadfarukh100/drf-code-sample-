import datetime as dt
from unittest.mock import call
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone
from django.utils.translation import ugettext as _
from django.utils.translation import ugettext_lazy as _
from model_bakery import baker

from absence.emails import AbsenceSubmittedManager, AbsenceSubmittedForUser, AbsenceUpdated, GeneralAbsencePublished
from absence.models import EmployeeAbsence, GeneralAbsence, EmployeeAbsenceComment
from account.models import Employee, Department
from constants.db import ABSENCE_STATUS_CHOICES


class TestAbsenceSubmittedManager(TestCase):

    @patch('absence.emails.Email.__init__')
    def test___init__(self, __init__):
        submitted_to = baker.make(Employee, department=baker.make(Department), email='myemail@example.com')
        absence = baker.make(EmployeeAbsence, submitted_to=submitted_to)

        email = AbsenceSubmittedManager(absence)
        self.assertEqual(email.absence, absence)

        __init__.assert_called_once_with(to='myemail@example.com')

    def test_get_context(self):
        submitted_to = baker.make(Employee, department=baker.make(Department), first_name='Gorge', last_name='Ballay')
        submitted_for = baker.make(Employee, department=baker.make(Department), first_name='Nothing', last_name='more')
        absence = baker.make(EmployeeAbsence, submitted_to=submitted_to, submitted_for=submitted_for)

        email = AbsenceSubmittedManager(absence)
        context = email.get_context()

        self.assertDictEqual(context, dict(submitted_to_first_name='Gorge',
                                           submitted_for_full_name='Nothing more',
                                           link=f'frontend_test/absences/{absence.id}/view',
                                           language='nb'))

    def test_subject(self):
        submitted_to = baker.make(Employee, department=baker.make(Department), email='myemail@example.com')
        absence = baker.make(EmployeeAbsence, submitted_to=submitted_to)
        email = AbsenceSubmittedManager(absence)

        self.assertEqual(email.subject, _('ABSENCE_SUBMITTED_TO_MANAGER'))

    def test_template(self):
        submitted_to = baker.make(Employee, department=baker.make(Department), email='myemail@example.com')
        absence = baker.make(EmployeeAbsence, submitted_to=submitted_to)
        email = AbsenceSubmittedManager(absence)

        self.assertEqual(email.template, 'ABSENCE_SUBMITTED_MANAGER')


class TestAbsenceSubmittedForUser(TestCase):

    @patch('absence.emails.Email.__init__')
    def test___init__(self, __init__):
        submitted_for = baker.make(Employee, department=baker.make(Department), email='myemail@example.com')
        absence = baker.make(EmployeeAbsence, submitted_for=submitted_for)

        email = AbsenceSubmittedForUser(absence)
        self.assertEqual(email.absence, absence)

        __init__.assert_called_once_with(to='myemail@example.com')

    def test_get_context(self):
        submitted_for = baker.make(Employee, department=baker.make(Department), first_name='Gorge', last_name='Ballay')
        submitted_by = baker.make(Employee, department=baker.make(Department), first_name='Nothing', last_name='more')
        absence = baker.make(EmployeeAbsence, submitted_for=submitted_for, submitted_by=submitted_by)

        email = AbsenceSubmittedForUser(absence)
        context = email.get_context()

        self.assertDictEqual(context, dict(submitted_for_first_name='Gorge',
                                           submitted_by_full_name='Nothing more',
                                           link=f'frontend_test/absences/{absence.id}/view',
                                           language='nb'))

    def test_subject(self):
        submitted_for = baker.make(Employee, department=baker.make(Department), email='myemail@example.com')
        absence = baker.make(EmployeeAbsence, submitted_for=submitted_for)
        email = AbsenceSubmittedForUser(absence)

        self.assertEqual(email.subject, _('ABSENCE_SUBMITTED_FOR_USER'))

    def test_template(self):
        submitted_for = baker.make(Employee, department=baker.make(Department), email='myemail@example.com')
        absence = baker.make(EmployeeAbsence, submitted_for=submitted_for)
        email = AbsenceSubmittedForUser(absence)

        self.assertEqual(email.template, 'ABSENCE_SUBMITTED_FOR_USER')


class TestAbsenceUpdated(TestCase):

    @patch('absence.emails.Email.__init__')
    def test___init__(self, __init__):
        submitted_for = baker.make(Employee, department=baker.make(Department), email='myemail@example.com')
        absence = baker.make(EmployeeAbsence, submitted_for=submitted_for)
        comment = baker.make(EmployeeAbsenceComment, absence=absence)

        email = AbsenceUpdated(absence, comment)
        self.assertEqual(email.absence, absence)
        self.assertEqual(email.comment, comment)

        __init__.assert_called_once_with(to='myemail@example.com')

    def test_get_context(self):
        submitted_for = baker.make(Employee, department=baker.make(Department), first_name='Gorge', last_name='Ballay')
        submitted_to = baker.make(Employee, department=baker.make(Department), first_name='Nothing', last_name='more')
        absence = baker.make(EmployeeAbsence, submitted_for=submitted_for,
                             submitted_to=submitted_to, status=ABSENCE_STATUS_CHOICES.APPROVED)
        comment = baker.make(EmployeeAbsenceComment, absence=absence,
                             commented_by=baker.make(Employee, department=baker.make(Department), first_name='Morgan', last_name='Ballay'))

        email = AbsenceUpdated(absence, comment)
        context = email.get_context()

        self.assertDictEqual(context, dict(submitted_for_first_name='Gorge',
                                           submitted_to_full_name='Nothing more',
                                           update_by_full_name='Morgan Ballay',
                                           status=_('APPROVED'),
                                           link=f'frontend_test/absences/{absence.id}/view',
                                           language='nb'))

    def test_subject(self):
        submitted_for = baker.make(Employee, department=baker.make(Department), email='myemail@example.com')
        absence = baker.make(EmployeeAbsence, submitted_for=submitted_for)
        comment = baker.make(EmployeeAbsenceComment, absence=absence)
        email = AbsenceUpdated(absence, comment)

        self.assertEqual(email.subject, _('ABSENCE_STATUS_HAS_BEEN_UPDATED'))

    def test_template(self):
        submitted_for = baker.make(Employee, department=baker.make(Department), email='myemail@example.com')
        absence = baker.make(EmployeeAbsence, submitted_for=submitted_for)
        comment = baker.make(EmployeeAbsenceComment, absence=absence)
        email = AbsenceUpdated(absence, comment)

        self.assertEqual(email.template, 'ABSENCE_STATUS_UPDATED')


class TestGeneralAbsencePublished(TestCase):

    @patch('absence.emails.MakeEmail.__init__')
    def test___init__(self, __init__):
        absence = baker.make(GeneralAbsence)

        email = GeneralAbsencePublished(absence=absence, iterable=[])
        self.assertEqual(email.instance, absence)

        __init__.assert_called_once_with(iterable=[])

    @patch('absence.emails.formatted_date')
    def test_get_context(self, _formatted_date):
        submitted_by = baker.make(Employee, department=baker.make(Department), first_name='Nothing', last_name='more')

        absence = baker.make(GeneralAbsence,
                             start=timezone.make_aware(dt.datetime(2020, 5, 5, 1, 0, 0)),
                             end=timezone.make_aware(dt.datetime(2020, 5, 10, 23, 0, 0)),
                             submitted_by=submitted_by)

        _formatted_date.side_effect = ['05/05/2020', '10/05/2020']

        email = GeneralAbsencePublished(absence=absence, iterable=[])
        context = email.get_context()

        self.assertDictEqual(context, dict(manager_name='Nothing more',
                                           start_date='05/05/2020',
                                           end_date='10/05/2020',
                                           duration=6,
                                           link=f'frontend_test/absences?id={absence.id}'))

        self.assertEqual(_formatted_date.mock_calls,
                         [call(dt.date(2020, 5, 5)),
                          call(dt.date(2020, 5, 10))])

    @patch('absence.emails.MakeEmail.make_context')
    def test_make_context(self, _make_context):
        absence = baker.make(GeneralAbsence)
        email = GeneralAbsencePublished(absence=absence, iterable=[])
        employee = baker.make(Employee, department=baker.make(Department), first_name='First Name')

        _make_context.return_value = dict()

        context = email.make_context(employee)
        self.assertDictEqual(context, dict(first_name='First Name', language='nb'))

        _make_context.assert_called_once()

    def test_make_to(self):
        absence = baker.make(GeneralAbsence)
        email = GeneralAbsencePublished(absence=absence, iterable=[])
        employee = baker.make(Employee, department=baker.make(Department), email='myemail@example.com')

        res = email.make_to(employee)
        self.assertEqual(res, 'myemail@example.com')

    def test_subject(self):
        absence = baker.make(GeneralAbsence)
        email = GeneralAbsencePublished(absence=absence, iterable=[])

        self.assertEqual(email.subject, _('ABSENCE_PUBLISHED_EMAIL_SUBJECT'))

    def test_template(self):
        absence = baker.make(GeneralAbsence)
        email = GeneralAbsencePublished(absence=absence, iterable=[])

        self.assertEqual(email.template, 'GENERAL_ABSENCE_PUBLISHED')
