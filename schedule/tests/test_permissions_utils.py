import datetime as dt
import random
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone
from freezegun import freeze_time
from model_bakery import baker

from account.models import Company
from account.models import Employee, Department
from constants.db import SCHEDULE_STATUS_CHOICES
from schedule.models import Schedule
from schedule.permissions_utils import is_user_allocated_in_schedule, \
    is_user_same_department_of_schedule_or_allocated_in, is_user_same_department_of_schedule, is_schedule_published, \
    is_schedule_end_after_user_created, schedule_for_employee, schedule_for_staff_or_allocated_in, schedule_for_manager, \
    can_retrieve_schedule, can_update_schedule, can_view_schedule_feedback, can_list_schedule_history, \
    can_stop_collecting_preferences, schedule_for_staff, can_delete_schedule, \
    can_collect_preferences_schedule, can_publish_schedule, can_request_schedule
from shift.models import Shift


class TestPermissionUtils(TestCase):
    def test_is_user_allocated_in_schedule(self):
        user_1 = baker.make(Employee, department=baker.make(Department))
        user_2 = baker.make(Employee, department=baker.make(Department))

        status_choices = [SCHEDULE_STATUS_CHOICES.ENTERING_DETAILS, SCHEDULE_STATUS_CHOICES.COLLECTING_PREFERENCE,
                          SCHEDULE_STATUS_CHOICES.PRODUCING_SCHEDULE, SCHEDULE_STATUS_CHOICES.REVIEWING_SCHEDULE]

        schedule_1 = baker.make(Schedule, status=SCHEDULE_STATUS_CHOICES.PUBLISHED)
        schedule_2 = baker.make(Schedule, status=SCHEDULE_STATUS_CHOICES.PUBLISHED)
        schedule_3 = baker.make(Schedule, status=random.choice(status_choices))
        schedule_4 = baker.make(Schedule, status=random.choice(status_choices))

        shift_1 = baker.make(Shift, schedule=schedule_1)
        shift_2 = baker.make(Shift, schedule=schedule_2)
        shift_3 = baker.make(Shift, schedule=schedule_3)
        shift_4 = baker.make(Shift, schedule=schedule_4)

        shift_1.employees_allocated.add(user_1)
        shift_2.employees_allocated.add(user_2)
        shift_3.employees_allocated.add(user_2)
        shift_4.employees_allocated.add(user_2)

        self.assertTrue(is_user_allocated_in_schedule(user_1, schedule_1))
        self.assertTrue(is_user_allocated_in_schedule(user_2, schedule_2))
        self.assertFalse(is_user_allocated_in_schedule(user_1, schedule_2))
        self.assertFalse(is_user_allocated_in_schedule(user_2, schedule_1))

    @patch('schedule.permissions_utils.is_user_allocated_in_schedule')
    def test_is_user_same_department_of_schedule_or_allocated_in(self, _is_user_allocated_in_schedule):
        department = baker.make(Department)
        user_1 = baker.make(Employee, department=department)
        user_2 = baker.make(Employee, department=baker.make(Department))
        schedule_1 = baker.make(Schedule, department=department)
        schedule_2 = baker.make(Schedule, department=baker.make(Department))

        _is_user_allocated_in_schedule.return_value = False
        self.assertTrue(is_user_same_department_of_schedule_or_allocated_in(user_1, schedule_1))
        self.assertFalse(is_user_same_department_of_schedule_or_allocated_in(user_2, schedule_2))

        _is_user_allocated_in_schedule.return_value = True
        self.assertTrue(is_user_same_department_of_schedule_or_allocated_in(user_1, schedule_1))
        self.assertTrue(is_user_same_department_of_schedule_or_allocated_in(user_2, schedule_2))

        _is_user_allocated_in_schedule.assert_called()

    def test_is_user_same_department_of_schedule(self):
        department = baker.make(Department)
        user_1 = baker.make(Employee, department=department)
        user_2 = baker.make(Employee, department=baker.make(Department))
        schedule_1 = baker.make(Schedule, department=department)
        schedule_2 = baker.make(Schedule, department=baker.make(Department))

        self.assertTrue(is_user_same_department_of_schedule(user_1, schedule_1))
        self.assertFalse(is_user_same_department_of_schedule(user_2, schedule_2))

    def test_is_schedule_published(self):
        status_choices = [SCHEDULE_STATUS_CHOICES.ENTERING_DETAILS, SCHEDULE_STATUS_CHOICES.COLLECTING_PREFERENCE,
                          SCHEDULE_STATUS_CHOICES.PRODUCING_SCHEDULE, SCHEDULE_STATUS_CHOICES.REVIEWING_SCHEDULE]

        schedule_1 = baker.make(Schedule, status=random.choice(status_choices))
        schedule_2 = baker.make(Schedule, status=SCHEDULE_STATUS_CHOICES.PUBLISHED)

        self.assertFalse(is_schedule_published(schedule_1))
        self.assertTrue(is_schedule_published(schedule_2))

    def test_is_schedule_end_after_user_created(self):
        end = timezone.make_aware(dt.datetime(2020, 1, 1, 5, 0, 0))

        schedule = baker.make(Schedule, end=end)

        with freeze_time("2020-01-01 09:00:00"):
            user_1 = baker.make(Employee, department=baker.make(Department))
        with freeze_time("2020-01-01 00:00:00"):
            user_2 = baker.make(Employee, department=baker.make(Department))

        self.assertFalse(is_schedule_end_after_user_created(user_1, schedule))
        self.assertTrue(is_schedule_end_after_user_created(user_2, schedule))

    @patch('schedule.permissions_utils.is_schedule_end_after_user_created')
    @patch('schedule.permissions_utils.is_schedule_published')
    @patch('schedule.permissions_utils.is_user_same_department_of_schedule_or_allocated_in')
    def test_schedule_for_employee(self, _is_user_same_department_of_schedule_or_allocated_in, _is_schedule_published,
                                   _is_schedule_end_after_user_created):
        user = baker.make(Employee, department=baker.make(Department))
        schedule = baker.make(Schedule)

        with patch.object(user, 'is_employee') as is_employee:
            is_employee.return_value = False

            _is_user_same_department_of_schedule_or_allocated_in.return_value = random.choice([True, False])
            _is_schedule_published.return_value = random.choice([True, False])
            _is_schedule_end_after_user_created.return_value = random.choice([True, False])

            self.assertFalse(schedule_for_employee(user, schedule))

        with patch.object(user, 'is_employee') as is_employee:
            is_employee.return_value = True

            _is_user_same_department_of_schedule_or_allocated_in.return_value = False
            _is_schedule_published.return_value = random.choice([True, False])
            _is_schedule_end_after_user_created.return_value = random.choice([True, False])

            self.assertFalse(schedule_for_employee(user, schedule))

        with patch.object(user, 'is_employee') as is_employee:
            is_employee.return_value = True

            _is_user_same_department_of_schedule_or_allocated_in.return_value = True
            _is_schedule_published.return_value = False
            _is_schedule_end_after_user_created.return_value = random.choice([True, False])

            self.assertFalse(schedule_for_employee(user, schedule))

        with patch.object(user, 'is_employee') as is_employee:
            is_employee.return_value = True

            _is_user_same_department_of_schedule_or_allocated_in.return_value = True
            _is_schedule_published.return_value = True
            _is_schedule_end_after_user_created.return_value = False

            self.assertFalse(schedule_for_employee(user, schedule))

        with patch.object(user, 'is_employee') as is_employee:
            is_employee.return_value = True

            _is_user_same_department_of_schedule_or_allocated_in.return_value = True
            _is_schedule_published.return_value = True
            _is_schedule_end_after_user_created.return_value = True

            self.assertTrue(schedule_for_employee(user, schedule))

        _is_user_same_department_of_schedule_or_allocated_in.assert_called_with(user, schedule)
        _is_schedule_published.assert_called_with(schedule)
        _is_schedule_end_after_user_created.assert_called_with(user, schedule)

    @patch('schedule.permissions_utils.is_user_same_department_of_schedule_or_allocated_in')
    def test_schedule_for_staff_or_allocated_in(self, _is_user_same_department_of_schedule_or_allocated_in):
        schedule = baker.make(Schedule)
        user = baker.make(Employee, department=baker.make(Department))

        with patch.object(user, 'is_staff_') as is_staff_:
            is_staff_.return_value = False
            _is_user_same_department_of_schedule_or_allocated_in.return_value = random.choice([True, False])

            self.assertFalse(schedule_for_staff_or_allocated_in(user, schedule))

        with patch.object(user, 'is_staff_') as is_staff_:
            is_staff_.return_value = random.choice([True, False])
            _is_user_same_department_of_schedule_or_allocated_in.return_value = False

            self.assertFalse(schedule_for_staff_or_allocated_in(user, schedule))

        with patch.object(user, 'is_staff_') as is_staff_:
            is_staff_.return_value = True
            _is_user_same_department_of_schedule_or_allocated_in.return_value = True

            self.assertTrue(schedule_for_staff_or_allocated_in(user, schedule))

        _is_user_same_department_of_schedule_or_allocated_in.assert_called_with(user, schedule)

    @patch('schedule.permissions_utils.is_user_same_department_of_schedule')
    def test_schedule_for_staff(self, _is_user_same_department_of_schedule):
        schedule = baker.make(Schedule)
        user = baker.make(Employee, department=baker.make(Department))

        with patch.object(user, 'is_staff_') as is_staff_:
            is_staff_.return_value = False
            _is_user_same_department_of_schedule.return_value = random.choice([True, False])

            self.assertFalse(schedule_for_staff(user, schedule))

        with patch.object(user, 'is_staff_') as is_staff_:
            is_staff_.return_value = random.choice([True, False])
            _is_user_same_department_of_schedule.return_value = False

            self.assertFalse(schedule_for_staff(user, schedule))

        with patch.object(user, 'is_staff_') as is_staff_:
            is_staff_.return_value = True
            _is_user_same_department_of_schedule.return_value = True

            self.assertTrue(schedule_for_staff(user, schedule))

        _is_user_same_department_of_schedule.assert_called_with(user, schedule)

    def test_schedule_for_manager(self):
        company = baker.make(Company)

        schedule_1 = baker.make(Schedule, department=baker.make(Department, company=company))
        schedule_2 = baker.make(Schedule, department=baker.make(Department, company=baker.make(Company)))
        user = baker.make(Employee, department=baker.make(Department), company=company)

        with patch.object(user, 'is_manager_admin_or_manager') as is_manager_admin_or_manager:
            is_manager_admin_or_manager.return_value = random.choice([True, False])

            self.assertFalse(schedule_for_manager(user, schedule_2))

        with patch.object(user, 'is_manager_admin_or_manager') as is_manager_admin_or_manager:
            is_manager_admin_or_manager.return_value = False

            self.assertFalse(schedule_for_manager(user, random.choice([schedule_1, schedule_2])))

        with patch.object(user, 'is_manager_admin_or_manager') as is_manager_admin_or_manager:
            is_manager_admin_or_manager.return_value = True
            self.assertTrue(schedule_for_manager(user, schedule_1))

    @patch('schedule.permissions_utils.schedule_for_manager')
    @patch('schedule.permissions_utils.schedule_for_staff_or_allocated_in')
    @patch('schedule.permissions_utils.schedule_for_employee')
    def test_can_retrieve_schedule(self, _schedule_for_employee, _schedule_for_staff_or_allocated_in,
                                   _schedule_for_manager):
        schedule = baker.make(Schedule)
        user = baker.make(Employee, department=baker.make(Department))

        _schedule_for_employee.return_value = True
        _schedule_for_staff_or_allocated_in.return_value = random.choice([True, False])
        _schedule_for_manager.return_value = random.choice([True, False])
        self.assertTrue(can_retrieve_schedule(user, schedule))

        _schedule_for_employee.return_value = random.choice([True, False])
        _schedule_for_staff_or_allocated_in.return_value = True
        _schedule_for_manager.return_value = random.choice([True, False])
        self.assertTrue(can_retrieve_schedule(user, schedule))

        _schedule_for_employee.return_value = random.choice([True, False])
        _schedule_for_staff_or_allocated_in.return_value = random.choice([True, False])
        _schedule_for_manager.return_value = True
        self.assertTrue(can_retrieve_schedule(user, schedule))

        _schedule_for_employee.return_value = False
        _schedule_for_staff_or_allocated_in.return_value = False
        _schedule_for_manager.return_value = False
        self.assertFalse(can_retrieve_schedule(user, schedule))

        _schedule_for_employee.assert_called_with(user, schedule)
        _schedule_for_staff_or_allocated_in.assert_called_with(user, schedule)
        _schedule_for_manager.assert_called_with(user, schedule)

    @patch('schedule.permissions_utils.schedule_for_manager')
    @patch('schedule.permissions_utils.schedule_for_staff')
    def test_can_update_schedule(self, _schedule_for_staff, _schedule_for_manager):
        schedule = baker.make(Schedule)
        user = baker.make(Employee, department=baker.make(Department))

        _schedule_for_staff.return_value = True
        _schedule_for_manager.return_value = random.choice([True, False])
        self.assertTrue(can_update_schedule(user, schedule))

        _schedule_for_staff.return_value = random.choice([True, False])
        _schedule_for_manager.return_value = True
        self.assertTrue(can_update_schedule(user, schedule))

        _schedule_for_staff.return_value = False
        _schedule_for_manager.return_value = False
        self.assertFalse(can_update_schedule(user, schedule))

        _schedule_for_staff.assert_called_with(user, schedule)
        _schedule_for_manager.assert_called_with(user, schedule)

    @patch('schedule.permissions_utils.schedule_for_manager')
    @patch('schedule.permissions_utils.schedule_for_staff')
    def test_can_collect_preferences_schedule(self, _schedule_for_staff, _schedule_for_manager):
        status_choices = [SCHEDULE_STATUS_CHOICES.COLLECTING_PREFERENCE, SCHEDULE_STATUS_CHOICES.PRODUCING_SCHEDULE,
                          SCHEDULE_STATUS_CHOICES.REVIEWING_SCHEDULE, SCHEDULE_STATUS_CHOICES.PUBLISHED]

        schedule_1 = baker.make(Schedule,
                                status=random.choice(status_choices),
                                collect_preferences=random.choice([True, False]))
        schedule_2 = baker.make(Schedule,
                                status=SCHEDULE_STATUS_CHOICES.ENTERING_DETAILS,
                                collect_preferences=False)
        schedule_3 = baker.make(Schedule,
                                status=random.choice(status_choices),
                                collect_preferences=True)
        schedule_4 = baker.make(Schedule,
                                status=SCHEDULE_STATUS_CHOICES.ENTERING_DETAILS,
                                collect_preferences=True)

        user = baker.make(Employee, department=baker.make(Department))

        _schedule_for_staff.return_value = random.choice([True, False])
        _schedule_for_manager.return_value = random.choice([True, False])
        self.assertFalse(can_collect_preferences_schedule(user, random.choice([schedule_1, schedule_2, schedule_3])))

        _schedule_for_staff.return_value = True
        _schedule_for_manager.return_value = True
        self.assertFalse(can_collect_preferences_schedule(user, random.choice([schedule_1, schedule_2, schedule_3])))

        _schedule_for_staff.return_value = random.choice([True, False])
        _schedule_for_manager.return_value = True
        self.assertFalse(can_collect_preferences_schedule(user, random.choice([schedule_1, schedule_2, schedule_3])))

        _schedule_for_staff.return_value = True
        _schedule_for_manager.return_value = random.choice([True, False])
        self.assertFalse(can_collect_preferences_schedule(user, random.choice([schedule_1, schedule_2, schedule_3])))

        _schedule_for_staff.return_value = True
        _schedule_for_manager.return_value = True
        self.assertTrue(can_collect_preferences_schedule(user, schedule_4))

        _schedule_for_staff.return_value = False
        _schedule_for_manager.return_value = True
        self.assertTrue(can_collect_preferences_schedule(user, schedule_4))

        _schedule_for_staff.return_value = True
        _schedule_for_manager.return_value = False
        self.assertTrue(can_collect_preferences_schedule(user, schedule_4))

        _schedule_for_staff.return_value = False
        _schedule_for_manager.return_value = False
        self.assertFalse(can_collect_preferences_schedule(user, schedule_4))

        _schedule_for_staff.assert_called()
        _schedule_for_manager.assert_called()

    @patch('schedule.permissions_utils.schedule_for_manager')
    @patch('schedule.permissions_utils.schedule_for_staff')
    def test_can_request_schedule(self, _schedule_for_staff, _schedule_for_manager):
        status_choices = [SCHEDULE_STATUS_CHOICES.COLLECTING_PREFERENCE, SCHEDULE_STATUS_CHOICES.PRODUCING_SCHEDULE,
                          SCHEDULE_STATUS_CHOICES.REVIEWING_SCHEDULE, SCHEDULE_STATUS_CHOICES.PUBLISHED]

        schedule_1 = baker.make(Schedule,
                                status=random.choice(status_choices),
                                collect_preferences=random.choice([True, False]))
        schedule_2 = baker.make(Schedule,
                                status=SCHEDULE_STATUS_CHOICES.ENTERING_DETAILS,
                                collect_preferences=True)
        schedule_3 = baker.make(Schedule,
                                status=random.choice(status_choices),
                                collect_preferences=True)
        schedule_4 = baker.make(Schedule,
                                status=SCHEDULE_STATUS_CHOICES.ENTERING_DETAILS,
                                collect_preferences=False)

        user = baker.make(Employee, department=baker.make(Department))

        _schedule_for_staff.return_value = random.choice([True, False])
        _schedule_for_manager.return_value = random.choice([True, False])
        self.assertFalse(can_request_schedule(user, random.choice([schedule_1, schedule_2, schedule_3])))

        _schedule_for_staff.return_value = True
        _schedule_for_manager.return_value = True
        self.assertFalse(can_request_schedule(user, random.choice([schedule_1, schedule_2, schedule_3])))

        _schedule_for_staff.return_value = random.choice([True, False])
        _schedule_for_manager.return_value = True
        self.assertFalse(can_request_schedule(user, random.choice([schedule_1, schedule_2, schedule_3])))

        _schedule_for_staff.return_value = True
        _schedule_for_manager.return_value = random.choice([True, False])
        self.assertFalse(can_request_schedule(user, random.choice([schedule_1, schedule_2, schedule_3])))

        _schedule_for_staff.return_value = True
        _schedule_for_manager.return_value = True
        self.assertTrue(can_request_schedule(user, schedule_4))

        _schedule_for_staff.return_value = False
        _schedule_for_manager.return_value = True
        self.assertTrue(can_request_schedule(user, schedule_4))

        _schedule_for_staff.return_value = True
        _schedule_for_manager.return_value = False
        self.assertTrue(can_request_schedule(user, schedule_4))

        _schedule_for_staff.return_value = False
        _schedule_for_manager.return_value = False
        self.assertFalse(can_request_schedule(user, schedule_4))

        _schedule_for_staff.assert_called()
        _schedule_for_manager.assert_called()

    @patch('schedule.permissions_utils.schedule_for_manager')
    @patch('schedule.permissions_utils.schedule_for_staff')
    def test_can_publish_schedule(self, _schedule_for_staff, _schedule_for_manager):
        status_choices = [SCHEDULE_STATUS_CHOICES.COLLECTING_PREFERENCE, SCHEDULE_STATUS_CHOICES.PRODUCING_SCHEDULE,
                          SCHEDULE_STATUS_CHOICES.ENTERING_DETAILS, SCHEDULE_STATUS_CHOICES.PUBLISHED]

        schedule_1 = baker.make(Schedule, status=random.choice(status_choices))
        schedule_2 = baker.make(Schedule, status=SCHEDULE_STATUS_CHOICES.REVIEWING_SCHEDULE)

        user = baker.make(Employee, department=baker.make(Department))

        _schedule_for_staff.return_value = random.choice([True, False])
        _schedule_for_manager.return_value = random.choice([True, False])
        self.assertFalse(can_publish_schedule(user, schedule_1))

        _schedule_for_staff.return_value = True
        _schedule_for_manager.return_value = True
        self.assertFalse(can_publish_schedule(user, schedule_1))

        _schedule_for_staff.return_value = random.choice([True, False])
        _schedule_for_manager.return_value = True
        self.assertFalse(can_publish_schedule(user, schedule_1))

        _schedule_for_staff.return_value = True
        _schedule_for_manager.return_value = random.choice([True, False])
        self.assertFalse(can_publish_schedule(user, schedule_1))

        _schedule_for_staff.return_value = True
        _schedule_for_manager.return_value = True
        self.assertTrue(can_publish_schedule(user, schedule_2))

        _schedule_for_staff.return_value = False
        _schedule_for_manager.return_value = True
        self.assertTrue(can_publish_schedule(user, schedule_2))

        _schedule_for_staff.return_value = True
        _schedule_for_manager.return_value = False
        self.assertTrue(can_publish_schedule(user, schedule_2))

        _schedule_for_staff.return_value = False
        _schedule_for_manager.return_value = False
        self.assertFalse(can_publish_schedule(user, schedule_2))

        _schedule_for_staff.assert_called()
        _schedule_for_manager.assert_called()

    @patch('schedule.permissions_utils.can_update_schedule')
    def test_can_view_schedule_feedback(self, _can_update_schedule):
        schedule = baker.make(Schedule)
        user = baker.make(Employee, department=baker.make(Department))

        _can_update_schedule.return_value = False
        self.assertFalse(can_view_schedule_feedback(user, schedule))

        _can_update_schedule.return_value = True
        self.assertTrue(can_view_schedule_feedback(user, schedule))

        _can_update_schedule.assert_called_with(user, schedule)

    @patch('schedule.permissions_utils.can_update_schedule')
    def test_can_list_schedule_history(self, _can_update_schedule):
        schedule = baker.make(Schedule)
        user = baker.make(Employee, department=baker.make(Department))

        _can_update_schedule.return_value = False
        self.assertFalse(can_list_schedule_history(user, schedule))

        _can_update_schedule.return_value = True
        self.assertTrue(can_list_schedule_history(user, schedule))

        _can_update_schedule.assert_called_with(user, schedule)

    @patch('schedule.permissions_utils.schedule_for_manager')
    @patch('schedule.permissions_utils.schedule_for_staff')
    def test_can_delete_schedule(self, _schedule_for_staff, _schedule_for_manager):
        user = baker.make(Employee, department=baker.make(Department))

        status_choices = [SCHEDULE_STATUS_CHOICES.COLLECTING_PREFERENCE, SCHEDULE_STATUS_CHOICES.PRODUCING_SCHEDULE,
                          SCHEDULE_STATUS_CHOICES.REVIEWING_SCHEDULE, SCHEDULE_STATUS_CHOICES.ENTERING_DETAILS]

        schedule_1 = baker.make(Schedule, status=SCHEDULE_STATUS_CHOICES.PUBLISHED)
        schedule_2 = baker.make(Schedule, status=random.choice(status_choices))

        _schedule_for_staff.return_value = random.choice([True, False])
        _schedule_for_manager.return_value = random.choice([True, False])
        self.assertFalse((can_delete_schedule(user, schedule_1)))

        _schedule_for_staff.return_value = True
        _schedule_for_manager.return_value = random.choice([True, False])
        self.assertTrue((can_delete_schedule(user, schedule_2)))

        _schedule_for_staff.return_value = random.choice([True, False])
        _schedule_for_manager.return_value = True
        self.assertTrue((can_delete_schedule(user, schedule_2)))

        _schedule_for_staff.assert_called()
        _schedule_for_manager.assert_called()

    @patch('schedule.permissions_utils.schedule_for_manager')
    @patch('schedule.permissions_utils.schedule_for_staff')
    def test_can_stop_collecting_preferences(self, _schedule_for_staff, _schedule_for_manager):
        user = baker.make(Employee, department=baker.make(Department))

        status_choices = [SCHEDULE_STATUS_CHOICES.ENTERING_DETAILS, SCHEDULE_STATUS_CHOICES.PRODUCING_SCHEDULE,
                          SCHEDULE_STATUS_CHOICES.REVIEWING_SCHEDULE, SCHEDULE_STATUS_CHOICES.PUBLISHED]

        schedule_1 = baker.make(Schedule, status=random.choice(status_choices))
        schedule_2 = baker.make(Schedule, status=SCHEDULE_STATUS_CHOICES.COLLECTING_PREFERENCE)

        _schedule_for_staff.return_value = random.choice([True, False])
        _schedule_for_manager.return_value = random.choice([True, False])
        self.assertFalse((can_stop_collecting_preferences(user, schedule_1)))

        _schedule_for_staff.return_value = True
        _schedule_for_manager.return_value = random.choice([True, False])
        self.assertTrue((can_stop_collecting_preferences(user, schedule_2)))

        _schedule_for_staff.return_value = random.choice([True, False])
        _schedule_for_manager.return_value = True
        self.assertTrue((can_stop_collecting_preferences(user, schedule_2)))

        _schedule_for_staff.assert_called()
        _schedule_for_manager.assert_called()
