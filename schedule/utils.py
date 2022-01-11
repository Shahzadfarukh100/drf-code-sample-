import datetime as dt
import math

import pytz
from django.utils import timezone

from account.utils import send_welcome_email
from schedule.emails import CollectPreferencesEmail, SchedulePublishedEmail
from schedule.models import Schedule
from shift_type.models import ShiftType


def get_schedule_feedback_stats(employee_feedback):
    # to prevent extra queries
    all_feedback = employee_feedback.values_list('rating', flat=True)
    all_feedback = list(all_feedback)
    average = 0
    percentages = [len([f for f in all_feedback if f == r]) for r in range(5, 0, -1)]
    if len(all_feedback):
        percentages = [math.floor((p / len(all_feedback)) * 100) for p in percentages]
        average = sum(all_feedback) / len(all_feedback)
    return {
        'percentages': percentages,
        'average': average
    }


def send_shift_notification_to_employee(start, end):
    # todo
    pass


def add_employee_to_schedules_shift_types_training(employee):
    current_and_future_schedules = Schedule.objects.filter(department=employee.department, end__gte=timezone.now())
    for schedule in current_and_future_schedules:
        shift_types_in_schedule = schedule.shift_types.all()

        for shift_type in shift_types_in_schedule:

            original_shift_type = ShiftType.objects.filter(id=shift_type.parent_shift_type_id).first()
            if original_shift_type is not None:
                is_trained_for_shift_type_family = original_shift_type.trained_employees.filter(id=employee.id).exists()

                if is_trained_for_shift_type_family:
                    shift_type.trained_employees.add(employee)


def send_email_on_collect_preferences_schedule(request_user, schedule):
    iterable = schedule.related_trained_employees.filter(is_active=False)

    send_welcome_email(request_user, iterable)
    preferences_email = CollectPreferencesEmail(schedule=schedule, iterable=iterable)
    preferences_email.send()


def send_email_on_publish_schedule(request_user, schedule):
    iterable = schedule.related_trained_employees.filter(is_active=False)

    send_welcome_email(request_user, iterable)

    published_email = SchedulePublishedEmail(schedule=schedule, iterable=iterable)
    published_email.send()


def adjust_schedule_timezone(date, time, user_timezone):
    tz = pytz.timezone(user_timezone)
    return tz.localize(dt.datetime.combine(date, time)).astimezone(pytz.utc)

