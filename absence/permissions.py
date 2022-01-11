from rolepermissions.checkers import has_permission, has_object_permission
from rolepermissions.permissions import register_object_checker

from absence.models import EmployeeAbsence, GeneralAbsence, EmployeeAbsenceType
from absence.permissions_utils import can_general_absence_retrieve, general_absence_for_employee, \
    general_absence_for_staff, can_general_absence_update, can_general_absence_delete, can_general_absence_restore
from account.models import Employee
from core.permissions import BasePermission
from core.roles import permission_names as perms


@register_object_checker()
def can_retrieve_absence(_, user: Employee, obj):
    if user.is_same_as(obj.submitted_for):
        return True

    if user.is_manager_admin() or user.is_manager():
        return user.belongs_to_company_of(obj)

    if user.is_staff_():
        return user.belongs_to_department_of(obj.submitted_for)


@register_object_checker()
def can_update_absence_status(_, user: Employee, obj: EmployeeAbsence):
    if user.is_manager_admin() or user.is_manager():
        return user.belongs_to_company_of(obj)
    if user.is_staff_():
        return (
                       (user == obj.submitted_by and user != obj.submitted_for) or
                       (user == obj.submitted_to and obj.submitted_to is not None) or
                       (user == obj.submitted_for and user != obj.submitted_by)
               ) and user.belongs_to_company_of(obj)


@register_object_checker()
def can_delete_absence(_, user: Employee, obj: EmployeeAbsence):
    return user.is_manager_admin() and user.belongs_to_company_of(obj)


@register_object_checker()
def can_list_absence_history(_, user: Employee, obj):
    if user.is_manager_admin() or user.is_manager():
        return user.belongs_to_company_of(obj)
    if user.is_staff_():
        return user.belongs_to_department_of(obj.submitted_for)
    if user.is_employee():
        return user == obj.submitted_for


class EmployeeAbsencePermission(BasePermission):
    def _has_permission(self, request, view):
        if view.action == 'list':
            return has_permission(request.user, perms.absence.view)
        if view.action == 'retrieve' or view.action == 'detail_history':
            return has_permission(request.user, perms.absence.view)
        if view.action == 'create':
            return has_permission(request.user, perms.absence.create)
        if view.action == 'destroy':
            return has_permission(request.user, perms.absence.delete)
        if view.action == 'requests':
            return has_permission(request.user, perms.absence.requests)
        if view.action == 'user_absences':
            return has_permission(request.user, perms.absence.user_absences)
        if view.action == 'approvals':
            return has_permission(request.user, perms.absence.approvals)
        if view.action == 'status':
            return has_permission(request.user, perms.absence.status)
        if view.action == 'export':
            return has_permission(request.user, perms.absence.export)
        if view.action == 'export_approvals':
            return has_permission(request.user, perms.absence.export_approvals)
        if view.action == 'history':
            return has_permission(request.user, perms.absence.history)
        raise NotImplementedError()

    def _has_object_permission(self, request, view, obj):
        if view.action in ('retrieve', 'detail_history', 'user_absences'):
            return has_object_permission('can_retrieve_absence', request.user, obj)
        if view.action == 'status':
            return has_object_permission('can_update_absence_status', request.user, obj)
        if view.action == 'destroy':
            return has_object_permission('can_delete_absence', request.user, obj)
        if view.action == 'history':
            return has_object_permission('can_list_absence_history', request.user, obj)

        raise NotImplementedError()


@register_object_checker()
def _can_retrieve_general_absence(_, user, obj):
    return can_general_absence_retrieve(user, obj)


@register_object_checker()
def _can_update_general_absence(_, user, obj):
    return can_general_absence_update(user, obj)


@register_object_checker()
def _can_delete_general_absence(_, user, obj):
    return can_general_absence_delete(user, obj)


@register_object_checker()
def _can_restore_general_absence(_, user, obj):
    return can_general_absence_restore(user, obj)


class GeneralAbsencePermissions(BasePermission):
    def _has_permission(self, request, view):
        if view.action == 'list':
            return has_permission(request.user, perms.general_absence.list)
        if view.action == 'retrieve':
            return has_permission(request.user, perms.general_absence.retrieve)
        if view.action == 'update':
            return has_permission(request.user, perms.general_absence.update)
        if view.action == 'create':
            return has_permission(request.user, perms.general_absence.create)
        if view.action == 'destroy':
            return has_permission(request.user, perms.general_absence.delete)
        if view.action == 'restore':
            return has_permission(request.user, perms.general_absence.restore)
        if view.action == 'archived':
            return has_permission(request.user, perms.general_absence.archived)
        if view.action == 'export_archived':
            return has_permission(request.user, perms.general_absence.export_archived)
        if view.action == 'export':
            return has_permission(request.user, perms.general_absence.export)

        raise NotImplementedError()

    def _has_object_permission(self, request, view, obj):
        if view.action == 'retrieve':
            return has_object_permission('_can_retrieve_general_absence', request.user, obj)
        if view.action == 'update':
            return has_object_permission('_can_update_general_absence', request.user, obj)
        if view.action == 'restore':
            return has_object_permission('_can_restore_general_absence', request.user, obj)
        if view.action == 'destroy':
            return has_object_permission('_can_delete_general_absence', request.user, obj)

        raise NotImplementedError()


@register_object_checker()
def can_retrieve_absence_type(_, user: Employee, obj: GeneralAbsence):
    return user.belongs_to_company_of(obj) and user.is_manager_admin() or user.is_manager()


@register_object_checker()
def can_update_absence_type(_, user: Employee, obj: EmployeeAbsenceType):
    return user.belongs_to_company_of(obj) and user.is_manager_admin() or user.is_manager()


@register_object_checker()
def can_delete_absence_type(_, user: Employee, obj: GeneralAbsence):
    return user.belongs_to_company_of(obj) and user.is_manager_admin() or user.is_manager()

@register_object_checker()
def can_mark_todo_complete(_, user: Employee, _obj):
    return user.is_manager_admin()

@register_object_checker()
def can_restore_absence_type(_, user: Employee, obj: GeneralAbsence):
    return user.belongs_to_company_of(obj) and user.is_manager_admin() or user.is_manager()


class EmployeeAbsenceTypePermission(BasePermission):
    def _has_permission(self, request, view):
        if view.action == 'list':
            return has_permission(request.user, perms.absence_type.view)
        if view.action == 'retrieve':
            return has_permission(request.user, perms.absence_type.view)
        if view.action == 'update':
            return has_permission(request.user, perms.absence_type.update)
        if view.action == 'create':
            return has_permission(request.user, perms.absence_type.create)
        if view.action == 'destroy':
            return has_permission(request.user, perms.absence_type.delete)
        if view.action == 'archived':
            return has_permission(request.user, perms.absence_type.archived)
        if view.action == 'restore':
            return has_permission(request.user, perms.absence_type.restore)
        if view.action == 'export':
            return has_permission(request.user, perms.absence_type.export)
        if view.action == 'export_archived':
            return has_permission(request.user, perms.absence_type.export)
        if view.action == 'mark_todo_complete':
            return has_permission(request.user, perms.absence_type.todo_complete)

        raise NotImplementedError()

    def _has_object_permission(self, request, view, obj):
        if view.action == 'retrieve':
            return has_object_permission('can_retrieve_absence_type', request.user, obj)
        if view.action == 'update':
            return has_object_permission('can_update_absence_type', request.user, obj)
        if view.action == 'restore':
            return has_object_permission('can_restore_absence_type', request.user, obj)
        if view.action == 'destroy':
            return has_object_permission('can_delete_absence_type', request.user, obj)
        if view.action == 'mark_todo_complete':
            return has_object_permission('can_mark_todo_complete', request.user, obj)

        raise NotImplementedError()
