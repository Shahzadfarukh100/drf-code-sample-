import random
from unittest.mock import patch

from django.test import TestCase
from model_bakery import baker

from absence.models import GeneralAbsence
from absence.permissions_utils import general_absence_company_check, general_absence_department_check, \
    general_absence_approved_check, general_absence_for_manager_admin_or_manager, general_absence_for_staff, \
    general_absence_for_employee, can_general_absence_retrieve, only_for_user_department, can_general_absence_update, \
    can_general_absence_delete, can_general_absence_restore
from account.models import Company
from account.models import Department
from account.tests.recipes import employee_recipe
from constants.db import COMPANY_ROLE_CHOICES, ABSENCE_STATUS_CHOICES


class TestPermissionUtils(TestCase):

    def test_general_absence_company_check(self):
        company = baker.make(Company)
        manager = employee_recipe.make(company=company)

        general_absence_1 = baker.make(GeneralAbsence)
        general_absence_2 = baker.make(GeneralAbsence)

        general_absence_1.department.add(baker.make(Department, company=company),
                                         baker.make(Department, company=company),
                                         baker.make(Department, company=company))



        self.assertTrue(general_absence_company_check(manager, general_absence_1))

        general_absence_1.department.add(baker.make(Department, company=company),
                                         baker.make(Department),
                                         baker.make(Department, company=baker.make(Company)))

        self.assertFalse(general_absence_company_check(manager, general_absence_2))


    def test_only_for_user_department(self):
        department = baker.make(Department)

        user_1 = employee_recipe.make(department=department)
        user_2 = employee_recipe.make(department=baker.make(Department))

        general_absence_1 = baker.make(GeneralAbsence)
        general_absence_2 = baker.make(GeneralAbsence)
        general_absence_3 = baker.make(GeneralAbsence)

        general_absence_1.department.add(department)
        general_absence_2.department.add(department, baker.make(Department), baker.make(Department))
        general_absence_3.department.add(baker.make(Department), baker.make(Department))


        self.assertFalse(only_for_user_department(random.choice([user_1, user_2]),
                                                  random.choice([general_absence_2, general_absence_3])
                                                  ))

        self.assertTrue(only_for_user_department(user_1, general_absence_1))




    def test_general_absence_department_check(self):

        department = baker.make(Department)
        staff = employee_recipe.make(department=department)

        general_absence_1 = baker.make(GeneralAbsence)
        general_absence_2 = baker.make(GeneralAbsence)

        general_absence_1.department.add(baker.make(Department),
                                         baker.make(Department),
                                         baker.make(Department),
                                         department)

        self.assertTrue(general_absence_department_check(staff, general_absence_1))

        general_absence_1.department.add(baker.make(Department),
                                         baker.make(Department),
                                         baker.make(Department))

        self.assertFalse(general_absence_department_check(staff, general_absence_2))



    def test_general_absence_approved_check(self):
        general_absence_1 = baker.make(GeneralAbsence, status=random.choice([ABSENCE_STATUS_CHOICES.PENDING, ABSENCE_STATUS_CHOICES.REJECTED, ABSENCE_STATUS_CHOICES.IN_REVIEW]))
        general_absence_2 = baker.make(GeneralAbsence, status=ABSENCE_STATUS_CHOICES.APPROVED)


        self.assertFalse(general_absence_approved_check(general_absence_1))
        self.assertTrue(general_absence_approved_check(general_absence_2))

    @patch('absence.permissions_utils.general_absence_company_check')
    def test_general_absence_for_manager_admin_or_manager(self, _general_absence_company_check):
        manager = employee_recipe.make(role=random.choice([COMPANY_ROLE_CHOICES.MANAGER_ADMIN, COMPANY_ROLE_CHOICES.MANAGER]))
        not_manager = employee_recipe.make(role=random.choice([COMPANY_ROLE_CHOICES.STAFF, COMPANY_ROLE_CHOICES.EMPLOYEE]))
        general_absence = baker.make(GeneralAbsence)

        _general_absence_company_check.return_value = False
        self.assertFalse(general_absence_for_manager_admin_or_manager(random.choice([manager, not_manager]), general_absence))


        _general_absence_company_check.return_value = random.choice([True, False])
        self.assertFalse(general_absence_for_manager_admin_or_manager(not_manager, general_absence))



        _general_absence_company_check.return_value = True
        self.assertTrue(general_absence_for_manager_admin_or_manager(manager, general_absence))

        _general_absence_company_check.assert_called_with(manager, general_absence)


    @patch('absence.permissions_utils.general_absence_department_check')
    @patch('absence.permissions_utils.general_absence_company_check')
    def test_general_absence_for_staff(self, _general_absence_company_check, _general_absence_department_check):
        not_staff = employee_recipe.make(role=random.choice([COMPANY_ROLE_CHOICES.MANAGER_ADMIN, COMPANY_ROLE_CHOICES.MANAGER, COMPANY_ROLE_CHOICES.EMPLOYEE]))
        staff = employee_recipe.make(role=COMPANY_ROLE_CHOICES.STAFF)
        general_absence = baker.make(GeneralAbsence)

        _general_absence_company_check.return_value = False
        _general_absence_department_check.return_value = random.choice([True, False])
        self.assertFalse(general_absence_for_staff(random.choice([not_staff, staff]), general_absence))


        _general_absence_company_check.return_value = random.choice([True, False])
        _general_absence_department_check.return_value = False
        self.assertFalse(general_absence_for_staff(random.choice([not_staff, staff]), general_absence))




        _general_absence_company_check.return_value = random.choice([True, False])
        _general_absence_department_check.return_value = random.choice([True, False])
        self.assertFalse(general_absence_for_staff(not_staff, general_absence))




        _general_absence_company_check.return_value = True
        _general_absence_department_check.return_value = True
        self.assertTrue(general_absence_for_staff(staff, general_absence))

        _general_absence_company_check.assert_called_with(staff, general_absence)
        _general_absence_department_check.assert_called_with(staff, general_absence)

    @patch('absence.permissions_utils.general_absence_approved_check')
    @patch('absence.permissions_utils.general_absence_department_check')
    @patch('absence.permissions_utils.general_absence_company_check')
    def test_general_absence_for_employee(self, _general_absence_company_check, _general_absence_department_check, _general_absence_approved_check):
        not_employee = employee_recipe.make(role=random.choice(
            [COMPANY_ROLE_CHOICES.MANAGER_ADMIN, COMPANY_ROLE_CHOICES.MANAGER, COMPANY_ROLE_CHOICES.STAFF]))
        employee = employee_recipe.make(role=COMPANY_ROLE_CHOICES.EMPLOYEE)
        general_absence = baker.make(GeneralAbsence)

        _general_absence_company_check.return_value = False
        _general_absence_department_check.return_value = random.choice([True, False])
        _general_absence_approved_check.return_value = random.choice([True, False])
        self.assertFalse(general_absence_for_employee(random.choice([not_employee, employee]), general_absence))



        _general_absence_company_check.return_value = random.choice([True, False])
        _general_absence_department_check.return_value = False
        _general_absence_approved_check.return_value = random.choice([True, False])
        self.assertFalse(general_absence_for_employee(random.choice([not_employee, employee]), general_absence))



        _general_absence_company_check.return_value = random.choice([True, False])
        _general_absence_department_check.return_value = random.choice([True, False])
        _general_absence_approved_check.return_value = False
        self.assertFalse(general_absence_for_employee(random.choice([not_employee, employee]), general_absence))




        _general_absence_company_check.return_value = random.choice([True, False])
        _general_absence_department_check.return_value = random.choice([True, False])
        _general_absence_approved_check.return_value = random.choice([True, False])
        self.assertFalse(general_absence_for_employee(not_employee, general_absence))





        _general_absence_company_check.return_value = True
        _general_absence_department_check.return_value = True
        _general_absence_approved_check.return_value = True
        self.assertTrue(general_absence_for_employee(employee, general_absence))




        _general_absence_company_check.assert_called_with(employee, general_absence)
        _general_absence_department_check.assert_called_with(employee, general_absence)
        _general_absence_approved_check.assert_called_with(general_absence)


    @patch('absence.permissions_utils.general_absence_for_employee')
    @patch('absence.permissions_utils.general_absence_for_staff')
    @patch('absence.permissions_utils.general_absence_for_manager_admin_or_manager')
    def test_can_general_absence_retrieve(self, _manager, _staff, _employee):
        general_absence = baker.make(GeneralAbsence)
        user = employee_recipe.make()

        _manager.return_value = True
        _staff.return_value = random.choice([True, False])
        _employee.return_value = random.choice([True, False])
        self.assertTrue(can_general_absence_retrieve(user, general_absence))


        _manager.return_value = random.choice([True, False])
        _staff.return_value = True
        _employee.return_value = random.choice([True, False])
        self.assertTrue(can_general_absence_retrieve(user, general_absence))


        _manager.return_value = random.choice([True, False])
        _staff.return_value = random.choice([True, False])
        _employee.return_value = True
        self.assertTrue(can_general_absence_retrieve(user, general_absence))


        _manager.return_value = False
        _staff.return_value = False
        _employee.return_value = False
        self.assertFalse(can_general_absence_retrieve(user, general_absence))

        _manager.assert_called_with(user, general_absence)
        _staff.assert_called_with(user, general_absence)
        _employee.assert_called_with(user, general_absence)

    @patch('absence.permissions_utils.only_for_user_department')
    @patch('absence.permissions_utils.general_absence_for_staff')
    @patch('absence.permissions_utils.general_absence_for_manager_admin_or_manager')
    def test_can_general_absence_update(self, for_manager_admin_or_manager, for_staff, for_user_department):
        general_absence = baker.make(GeneralAbsence)
        user = employee_recipe.make()

        for_manager_admin_or_manager.return_value = True
        for_staff.return_value = random.choice([True, False])
        for_user_department.return_value = random.choice([True, False])
        self.assertTrue(can_general_absence_update(user, general_absence))

        for_manager_admin_or_manager.return_value = False
        for_staff.return_value = True
        for_user_department.return_value = True
        self.assertTrue(can_general_absence_update(user, general_absence))

        for_manager_admin_or_manager.return_value = False
        for_staff.return_value = False
        for_user_department.return_value = random.choice([True, False])
        self.assertFalse(can_general_absence_update(user, general_absence))

        for_manager_admin_or_manager.return_value = False
        for_staff.return_value = random.choice([True, False])
        for_user_department.return_value = False
        self.assertFalse(can_general_absence_update(user, general_absence))

        for_manager_admin_or_manager.return_value = False
        for_staff.return_value = False
        for_user_department.return_value = False
        self.assertFalse(can_general_absence_update(user, general_absence))

        for_manager_admin_or_manager.return_value = False
        for_staff.return_value = True
        for_user_department.return_value = True
        self.assertTrue(can_general_absence_update(user, general_absence))

        for_manager_admin_or_manager.assert_called_with(user, general_absence)
        for_staff.assert_called_with(user, general_absence)
        for_user_department.assert_called_with(user, general_absence)

    @patch('absence.permissions_utils.only_for_user_department')
    @patch('absence.permissions_utils.general_absence_for_staff')
    @patch('absence.permissions_utils.general_absence_for_manager_admin_or_manager')
    def test_can_general_absence_delete(self, for_manager_admin_or_manager, for_staff, for_user_department):
        general_absence = baker.make(GeneralAbsence)
        user = employee_recipe.make()

        for_manager_admin_or_manager.return_value = True
        for_staff.return_value = random.choice([True, False])
        for_user_department.return_value = random.choice([True, False])
        self.assertTrue(can_general_absence_delete(user, general_absence))

        for_manager_admin_or_manager.return_value = False
        for_staff.return_value = True
        for_user_department.return_value = True
        self.assertTrue(can_general_absence_delete(user, general_absence))

        for_manager_admin_or_manager.return_value = False
        for_staff.return_value = False
        for_user_department.return_value = random.choice([True, False])
        self.assertFalse(can_general_absence_delete(user, general_absence))

        for_manager_admin_or_manager.return_value = False
        for_staff.return_value = random.choice([True, False])
        for_user_department.return_value = False
        self.assertFalse(can_general_absence_delete(user, general_absence))

        for_manager_admin_or_manager.return_value = False
        for_staff.return_value = False
        for_user_department.return_value = False
        self.assertFalse(can_general_absence_delete(user, general_absence))

        for_manager_admin_or_manager.return_value = False
        for_staff.return_value = True
        for_user_department.return_value = True
        self.assertTrue(can_general_absence_delete(user, general_absence))

        for_manager_admin_or_manager.assert_called_with(user, general_absence)
        for_staff.assert_called_with(user, general_absence)
        for_user_department.assert_called_with(user, general_absence)

    @patch('absence.permissions_utils.only_for_user_department')
    @patch('absence.permissions_utils.general_absence_for_staff')
    @patch('absence.permissions_utils.general_absence_for_manager_admin_or_manager')
    def test_can_general_absence_restore(self, for_manager_admin_or_manager, for_staff, for_user_department):
        general_absence = baker.make(GeneralAbsence)
        user = employee_recipe.make()

        for_manager_admin_or_manager.return_value = True
        for_staff.return_value = random.choice([True, False])
        for_user_department.return_value = random.choice([True, False])
        self.assertTrue(can_general_absence_restore(user, general_absence))

        for_manager_admin_or_manager.return_value = False
        for_staff.return_value = True
        for_user_department.return_value = True
        self.assertTrue(can_general_absence_restore(user, general_absence))

        for_manager_admin_or_manager.return_value = False
        for_staff.return_value = False
        for_user_department.return_value = random.choice([True, False])
        self.assertFalse(can_general_absence_restore(user, general_absence))

        for_manager_admin_or_manager.return_value = False
        for_staff.return_value = random.choice([True, False])
        for_user_department.return_value = False
        self.assertFalse(can_general_absence_restore(user, general_absence))

        for_manager_admin_or_manager.return_value = False
        for_staff.return_value = False
        for_user_department.return_value = False
        self.assertFalse(can_general_absence_restore(user, general_absence))

        for_manager_admin_or_manager.return_value = False
        for_staff.return_value = True
        for_user_department.return_value = True
        self.assertTrue(can_general_absence_restore(user, general_absence))

        for_manager_admin_or_manager.assert_called_with(user, general_absence)
        for_staff.assert_called_with(user, general_absence)
        for_user_department.assert_called_with(user, general_absence)





