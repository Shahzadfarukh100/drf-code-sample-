from operator import attrgetter

from django.test import TestCase
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from freezegun import freeze_time
from model_bakery import baker

from absence.models import *


class TestEmployeeAbsenceType(TestCase):

    def test_str(self):
        absence_type = baker.make(EmployeeAbsenceType, name='Test Employee Absence Type')
        self.assertEqual(str(absence_type), 'Test Employee Absence Type')


class TestEmployeeAbsence(TestCase):

    def test_get_event_queryset(self):
        self.maxDiff = None
        start_1 = timezone.make_aware(dt.datetime(2020, 1, 1, 0, 0))
        start_2 = timezone.make_aware(dt.datetime(2020, 2, 1, 0, 0))
        start_3 = timezone.make_aware(dt.datetime(2020, 3, 1, 0, 0))
        start_4 = timezone.make_aware(dt.datetime(2020, 4, 1, 0, 0))
        start_5 = timezone.make_aware(dt.datetime(2020, 5, 1, 0, 0))

        end_1 = timezone.make_aware(dt.datetime(2020, 1, 31, 0, 0))
        end_2 = timezone.make_aware(dt.datetime(2020, 2, 28, 0, 0))
        end_3 = timezone.make_aware(dt.datetime(2020, 3, 31, 0, 0))
        end_4 = timezone.make_aware(dt.datetime(2020, 4, 30, 0, 0))
        end_5 = timezone.make_aware(dt.datetime(2020, 5, 31, 0, 0))

        baker.make(EmployeeAbsence, start=start_1, end=end_1,
                   absence_type=baker.make(EmployeeAbsenceType, duration=DURATION.HOURLY)
                   )
        baker.make(EmployeeAbsence, start=start_2, end=end_2,
                   absence_type=baker.make(EmployeeAbsenceType)
                   )
        baker.make(EmployeeAbsence, start=start_3, end=end_3,
                   absence_type=baker.make(EmployeeAbsenceType, duration=DURATION.HOURLY)
                   )
        baker.make(EmployeeAbsence, start=start_4, end=end_4,
                   absence_type=baker.make(EmployeeAbsenceType)
                   )

        baker.make(EmployeeAbsence, start=start_5, end=end_5,
                   absence_type=baker.make(EmployeeAbsenceType,duration=DURATION.HOURLY)
                   )

        queryset = EmployeeAbsence.get_event_queryset(start__gte=start_2,
                                                      end__lt=end_5)
        self.assertQuerysetEqual(queryset,
                                 [
                                     (start_4, end_4, str(_('ABSENT')), '#E57373', 'ABSENCE',
                                      True),
                                     (start_3, end_3, str(_('ABSENT')), '#E57373', 'ABSENCE',
                                      False),
                                     (start_2, end_2, str(_('ABSENT')), '#E57373', 'ABSENCE',
                                      True),
                                 ],
                                 transform=attrgetter('start', 'end', 'title', 'background_color', 'type',
                                                      'allDay')
                                 )

    def test_get_end(self):
        end = timezone.make_aware(dt.datetime(2020, 1, 5, 0, 0))
        absence = baker.make(EmployeeAbsence, end=end)
        res = absence.get_end()
        self.assertEqual(res, timezone.make_aware(dt.datetime(2020, 1, 4, 0, 0)))

        end = timezone.make_aware(dt.datetime(2020, 1, 5, 12, 30))
        absence_type = baker.make(EmployeeAbsenceType, duration=DURATION.HOURLY)
        absence = baker.make(EmployeeAbsence, end=end, absence_type= absence_type)
        res = absence.get_end()
        self.assertEqual(res, timezone.make_aware(dt.datetime(2020, 1, 5, 12, 30)))


    def test_get_comments(self):
        absence = baker.make(EmployeeAbsence)
        baker.make(EmployeeAbsenceComment, absence=absence)
        baker.make(EmployeeAbsenceComment, absence=absence)
        baker.make(EmployeeAbsenceComment, absence=absence)
        baker.make(EmployeeAbsenceComment)
        baker.make(EmployeeAbsenceComment)

        res = absence.get_comments()
        self.assertEqual(res.count(), 3)

    @freeze_time("2020-04-27 09:00:00")
    def test_is_created_for_past(self):
        start = timezone.make_aware(dt.datetime(2020, 4, 25, 0, 0))
        absence = baker.make(EmployeeAbsence, start=start)
        self.assertTrue(absence.is_created_for_past())


        start = timezone.make_aware(dt.datetime(2020, 4, 28, 0, 0))
        absence = baker.make(EmployeeAbsence, start=start)
        self.assertFalse(absence.is_created_for_past())


class TestGeneralAbsence(TestCase):

    def test_get_event_queryset(self):
        self.maxDiff = None
        start_1 = timezone.make_aware(dt.datetime(2020, 1, 1, 0, 0))
        start_2 = timezone.make_aware(dt.datetime(2020, 2, 1, 0, 0))
        start_3 = timezone.make_aware(dt.datetime(2020, 3, 1, 0, 0))
        start_4 = timezone.make_aware(dt.datetime(2020, 4, 1, 0, 0))
        start_5 = timezone.make_aware(dt.datetime(2020, 5, 1, 0, 0))

        end_1 = timezone.make_aware(dt.datetime(2020, 1, 31, 0, 0))
        end_2 = timezone.make_aware(dt.datetime(2020, 2, 28, 0, 0))
        end_3 = timezone.make_aware(dt.datetime(2020, 3, 31, 0, 0))
        end_4 = timezone.make_aware(dt.datetime(2020, 4, 30, 0, 0))
        end_5 = timezone.make_aware(dt.datetime(2020, 5, 31, 0, 0))

        baker.make(GeneralAbsence, start=start_1, end=end_1)
        baker.make(GeneralAbsence, start=start_2, end=end_2)
        baker.make(GeneralAbsence, start=start_3, end=end_3)
        baker.make(GeneralAbsence, start=start_4, end=end_4)
        baker.make(GeneralAbsence, start=start_5, end=end_5)

        queryset = GeneralAbsence.get_event_queryset(start__gte=start_2, end__lt=end_5)

        self.assertQuerysetEqual(queryset,
                                 [
                                     (start_4, end_4, str(_('ABSENT')), '#E57373',
                                      'GENERAL_ABSENCE', True),
                                     (start_3, end_3, str(_('ABSENT')), '#E57373',
                                      'GENERAL_ABSENCE', True),
                                     (start_2, end_2, str(_('ABSENT')), '#E57373',
                                      'GENERAL_ABSENCE', True),
                                 ],
                                 transform=attrgetter('start', 'end', 'title', 'background_color', 'type',
                                                      'allDay')
                                 )
