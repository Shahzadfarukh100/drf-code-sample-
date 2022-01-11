from constants.db import SCHEDULE_STATUS_CHOICES


def is_user_allocated_in_schedule(user, obj):
    return user.allocated_in.filter(schedule=obj, schedule__status=SCHEDULE_STATUS_CHOICES.PUBLISHED).exists()


def is_user_same_department_of_schedule_or_allocated_in(user, obj):
    is_allocated_in = is_user_allocated_in_schedule(user, obj)

    return obj.department_id == user.department_id or is_allocated_in


def is_user_same_department_of_schedule(user, obj):
    return obj.department_id == user.department_id


def is_schedule_published(obj):
    return obj.status == SCHEDULE_STATUS_CHOICES.PUBLISHED


def is_schedule_end_after_user_created(user, obj):
    return obj.end >= user.created


def schedule_for_employee(user, obj):
    same_department = is_user_same_department_of_schedule_or_allocated_in(user, obj)
    is_published = is_schedule_published(obj)
    schedule_end_after_user_created = is_schedule_end_after_user_created(user, obj)

    return user.is_employee() and same_department and is_published and schedule_end_after_user_created


def schedule_for_staff_or_allocated_in(user, obj):
    same_department = is_user_same_department_of_schedule_or_allocated_in(user, obj)

    return user.is_staff_() and same_department


def schedule_for_staff(user, obj):
    same_department = is_user_same_department_of_schedule(user, obj)

    return user.is_staff_() and same_department


def schedule_for_manager(user, obj):
    return user.is_manager_admin_or_manager() and obj.department.company == user.company


def can_retrieve_schedule(user, obj):
    for_employee = schedule_for_employee(user, obj)
    for_staff = schedule_for_staff_or_allocated_in(user, obj)
    for_manager = schedule_for_manager(user, obj)

    return for_employee or for_staff or for_manager


def can_update_schedule(user, obj):
    for_staff = schedule_for_staff(user, obj)
    for_manager = schedule_for_manager(user, obj)

    return for_staff or for_manager



def can_stop_collecting_preferences(user, obj):
    for_staff = schedule_for_staff(user, obj)
    for_manager = schedule_for_manager(user, obj)

    return (for_staff or for_manager) and obj.status == SCHEDULE_STATUS_CHOICES.COLLECTING_PREFERENCE


def can_collect_preferences_schedule(user, obj):
    for_staff = schedule_for_staff(user, obj)
    for_manager = schedule_for_manager(user, obj)
    can_schedule = obj.status == SCHEDULE_STATUS_CHOICES.ENTERING_DETAILS and obj.collect_preferences

    return (for_staff or for_manager) and can_schedule


def can_request_schedule(user, obj):
    for_staff = schedule_for_staff(user, obj)
    for_manager = schedule_for_manager(user, obj)
    can_schedule = obj.status == SCHEDULE_STATUS_CHOICES.ENTERING_DETAILS and not obj.collect_preferences

    return (for_staff or for_manager) and can_schedule


def can_publish_schedule(user, obj):
    for_staff = schedule_for_staff(user, obj)
    for_manager = schedule_for_manager(user, obj)
    can_schedule = obj.status == SCHEDULE_STATUS_CHOICES.REVIEWING_SCHEDULE

    return (for_staff or for_manager) and can_schedule


def can_delete_schedule(user, obj):
    for_staff = schedule_for_staff(user, obj)
    for_manager = schedule_for_manager(user, obj)
    obj_can_be_deleted = obj.status in [SCHEDULE_STATUS_CHOICES.ENTERING_DETAILS,
                                        SCHEDULE_STATUS_CHOICES.COLLECTING_PREFERENCE,
                                        SCHEDULE_STATUS_CHOICES.PRODUCING_SCHEDULE,
                                        SCHEDULE_STATUS_CHOICES.REVIEWING_SCHEDULE]

    return (for_staff or for_manager) and obj_can_be_deleted


def can_view_schedule_feedback(user, obj):
    return can_update_schedule(user, obj)


def can_list_schedule_history(user, obj):
    return can_update_schedule(user, obj)
