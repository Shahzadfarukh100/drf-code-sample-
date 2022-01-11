from rolepermissions.checkers import has_permission, has_object_permission
from rolepermissions.permissions import register_object_checker

from core.permissions import BasePermission
from core.roles import permission_names as perms
from schedule.permissions_utils import (can_list_schedule_history, can_view_schedule_feedback, can_delete_schedule,
                                        can_stop_collecting_preferences, can_retrieve_schedule,
                                        can_collect_preferences_schedule,
                                        can_publish_schedule, can_request_schedule)


@register_object_checker()
def _can_retrieve_schedule(_role, user, obj):
    return can_retrieve_schedule(user, obj)


@register_object_checker()
def _can_publish_schedule(_role, user, obj):
    return can_publish_schedule(user, obj)


@register_object_checker()
def _can_collect_preferences_schedule(_role, user, obj):
    return can_collect_preferences_schedule(user, obj)


@register_object_checker()
def _can_stop_collecting_preferences(_role, user, obj):
    return can_stop_collecting_preferences(user, obj)


@register_object_checker()
def _request_schedule(_role, user, obj):
    return can_request_schedule(user, obj)


@register_object_checker()
def _can_delete_schedule(_role, user, obj):
    return can_delete_schedule(user, obj)


@register_object_checker()
def _can_view_schedule_feedback(_role, user, obj):
    return can_view_schedule_feedback(user, obj)


@register_object_checker()
def _can_list_schedule_history(_, user, obj):
    return can_list_schedule_history(user, obj)


class SchedulePermission(BasePermission):
    def _has_permission(self, request, view):
        if view.action in ['retrieve', 'events']:
            return has_permission(request.user, perms.schedule.retrieve)
        if view.action == 'list':
            return has_permission(request.user, perms.schedule.list)
        if view.action == 'create':
            return has_permission(request.user, perms.schedule.create)
        if view.action == 'destroy':
            return has_permission(request.user, perms.schedule.delete)
        if view.action == 'collect_preferences':
            return has_permission(request.user, perms.schedule.collect_preferences)
        if view.action == 'publish':
            return has_permission(request.user, perms.schedule.publish)
        if view.action in ['feedback', 'feedback_stats']:
            return has_permission(request.user, perms.schedule_feedback.view)
        if view.action == 'export':
            return has_permission(request.user, perms.schedule.export)
        if view.action == 'history':
            return has_permission(request.user, perms.schedule.history)
        if view.action == 'stop_collecting_preferences':
            return has_permission(request.user, perms.schedule.stop_collecting_preferences)
        if view.action == 'request_schedule':
            return has_permission(request.user, perms.schedule.request_schedule)
        raise NotImplementedError()

    def _has_object_permission(self, request, view, obj):
        if view.action in ['retrieve', 'events']:
            return has_object_permission('_can_retrieve_schedule', request.user, obj)
        if view.action == 'destroy':
            return has_object_permission('_can_delete_schedule', request.user, obj)
        if view.action == 'collect_preferences':
            return has_object_permission('_can_collect_preferences_schedule', request.user, obj)
        if view.action == 'publish':
            return has_object_permission('_can_publish_schedule', request.user, obj)
        if view.action in ['feedback', 'feedback_stats']:
            return has_object_permission('_can_view_schedule_feedback', request.user, obj)
        if view.action == 'history':
            return has_object_permission('_can_list_schedule_history', request.user, obj)
        if view.action == 'stop_collecting_preferences':
            return has_object_permission('_can_stop_collecting_preferences', request.user, obj)
        if view.action == 'request_schedule':
            return has_object_permission('_request_schedule', request.user, obj)
        raise NotImplementedError()
