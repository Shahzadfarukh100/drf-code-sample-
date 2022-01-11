from constants.db import ABSENCE_STATUS_CHOICES


def general_absence_company_check(user, obj):
    obj_company_list = list(set(obj.department.all().values_list('company_id', flat=True)))
    return len(obj_company_list) == 1 and str(user.company_id) == str(obj_company_list[0])

def only_for_user_department(user, obj):
    obj_department_list = list(set(obj.department.all().values_list('id', flat=True)))
    return len(obj_department_list) == 1 and str(user.department_id) == str(obj_department_list[0])

def general_absence_department_check(user, obj):
    return obj.department.all().filter(id=user.department_id).exists()


def general_absence_approved_check(obj):
    return obj.status == ABSENCE_STATUS_CHOICES.APPROVED


def general_absence_for_manager_admin_or_manager(user, obj):
    return user.is_manager_admin_or_manager() and general_absence_company_check(user, obj)

def general_absence_for_staff(user, obj):
    return user.is_staff_() and general_absence_company_check(user, obj) and general_absence_department_check(user, obj)

def general_absence_for_employee(user, obj):
    return (user.is_employee()
            and general_absence_company_check(user, obj)
            and general_absence_department_check(user, obj)
            and general_absence_approved_check(obj))


def can_general_absence_retrieve(user, obj):
    return (general_absence_for_manager_admin_or_manager(user, obj)
            or general_absence_for_staff(user, obj)
            or general_absence_for_employee(user, obj))

def can_general_absence_update(user, obj):
    return (general_absence_for_manager_admin_or_manager(user, obj) or
            (general_absence_for_staff(user, obj) and only_for_user_department(user, obj)))

def can_general_absence_delete(user, obj):
    return (general_absence_for_manager_admin_or_manager(user, obj) or
            (general_absence_for_staff(user, obj) and only_for_user_department(user, obj)))

def can_general_absence_restore(user, obj):
    return (general_absence_for_manager_admin_or_manager(user, obj) or
            (general_absence_for_staff(user, obj) and only_for_user_department(user, obj)))