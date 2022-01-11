import datetime as dt

from django.db.models import Q
from django.utils.translation import ugettext_lazy as _

from absence import emails
from absence.models import EmployeeAbsenceType, EmployeeAbsence, GeneralAbsence
from account.models import Employee
from constants.db import ABSENCE_STATUS_CHOICES, DURATION, ABSENCE_ENTITLEMENT_PERIOD_CHOICE
from core.verbs import (
    ABSENCE_SUBMITTED_TO_STAFFER, GENERAL_ABSENCE_CREATED, ABSENCE_STATUS_UPDATED,
    ABSENCE_UNDER_REVIEW, ABSENCE_SUBMITTED_FOR_USER
)
from helpers.formatting import formatted_date, formatted_datetime, local_datetime, local_date
from notification.utils import push_notification
from shift.utils import get_shift_events_queryset


def notify_manger_about_absence_submission(instance):
    if can_be_notify(instance):
        push_notification(ABSENCE_SUBMITTED_TO_STAFFER, instance.submitted_to_id, instance)
        email = emails.AbsenceSubmittedManager(absence=instance)
        email.send()


def notify_user_about_absence_submission_and_approved(instance):
    if can_be_notify(instance):
        push_notification(ABSENCE_SUBMITTED_FOR_USER, instance.submitted_for_id, instance)
        email = emails.AbsenceSubmittedForUser(absence=instance)
        email.send()


def notify_subordinate_about_absence_status_updated(instance, comment=None):
    if can_be_notify(instance):
        push_notification(ABSENCE_STATUS_UPDATED, instance.submitted_for_id, instance)
        email = emails.AbsenceUpdated(absence=instance, comment=comment)
        email.send()

def can_be_notify(instance):
    return instance.submitted_to != instance.submitted_for


def create_default_absence_types(company):
    absence = [
        dict(
            name=_('DAY_OFF'),
            description=_('DAY_OFF_ABSENCE'),
            entitlement=10,
            period=ABSENCE_ENTITLEMENT_PERIOD_CHOICE.PER_YEAR,
            submit_before_days=0,
            paid=False,
            company=company
        ), dict(
            name=_('ABSENCE'),
            description=_('ABSENCE'),
            entitlement=10,
            period=ABSENCE_ENTITLEMENT_PERIOD_CHOICE.PER_YEAR,
            submit_before_days=0,
            paid=False,
            company=company
        ), dict(
            name=_('QUITTING'),
            description=_('QUITTING_ABSENCE'),
            entitlement=0,
            period=ABSENCE_ENTITLEMENT_PERIOD_CHOICE.PER_YEAR,
            duration=DURATION.QUITTING,
            submit_before_days=7,
            paid=False,
            company=company
        ), dict(
            name=_('SICK_ABSENCE'),
            description=_('SICK_ABSENCE'),
            entitlement=0,
            period=ABSENCE_ENTITLEMENT_PERIOD_CHOICE.PER_YEAR,
            submit_before_days=0,
            paid=False,
            company=company
        ), dict(
            name=_('ANNUAL_ABSENCE'),
            description=_('ANNUAL_ABSENCE'),
            entitlement=0,
            period=ABSENCE_ENTITLEMENT_PERIOD_CHOICE.PER_YEAR,
            submit_before_days=7,
            paid=False,
            company=company
        ), dict(
            name=_('ABSENT_FROM_SHIFT'),
            description=_('ABSENT_FROM_SHIFT'),
            entitlement=0,
            period=ABSENCE_ENTITLEMENT_PERIOD_CHOICE.PER_YEAR,
            submit_before_days=0,
            paid=False,
            duration= DURATION.SHIFT,
            company=company
        )
    ]

    for absence in absence:
        EmployeeAbsenceType.objects.create(**absence)


def get_leaves_duration(start_date, end_date):
    return (end_date - start_date).days


def get_leave_start(absence):
    if absence.is_hourly():
        return formatted_datetime(local_datetime(absence.start))
    return formatted_date(absence.start)


def get_leave_end(absence):
    if absence.is_hourly():
        return formatted_datetime(local_datetime(absence.end))
    return formatted_date(absence.end - dt.timedelta(seconds=1))


def get_leaves_duration_string(absence):
    start, end = absence.start, absence.end

    td = (end - start)
    days, hours, minutes = td.days, td.seconds // 3600, (td.seconds // 60) % 60

    res = ''
    if days > 0:
        if days == 1:
            res += str(days) + ' ' + _('DAY').format()
        else:
            res += str(days) + ' ' + _('DAYS').format()

    if hours > 0:
        if hours == 1:
            res += ' ' + str(hours) + ' ' + _('HOUR').format()
        else:
            res += ' ' + str(hours) + ' ' + _('HOURS').format()
    if minutes > 0:
        if minutes == 1:
            res += ' ' + str(minutes) + ' ' + _('MINUTE').format()
        else:
            res += ' ' + str(minutes) + ' ' + _('MINUTES').format()
    res = res.strip()
    return " ".join(res.split())


def get_already_taken_leaves(absence, status):
    year = dt.datetime.now().year
    start_date = dt.datetime(year=year, month=1, day=1)
    end_date = dt.datetime(year=year, month=12, day=31)

    leaves_taken = get_overlap_absences(start_date, end_date, absence.submitted_for, status)

    number_of_leaves = 0
    for leave in leaves_taken:
        number_of_leaves += (leave.end - leave.start).days
    return number_of_leaves


def get_week_start(date):
    return date - dt.timedelta(days=date.weekday())


def get_week_end(date):
    start = date - dt.timedelta(days=date.weekday())
    end = start + dt.timedelta(days=7)
    return end

def get_consumed_absence(absences):
    absence_consumed = 0
    for r in absences:
        absence_consumed += get_leaves_duration(r.start, r.end)
    return absence_consumed


def generate_series_between_two_dates(start, end, freq='W-MON'):
    import pandas as pd
    return list(pd.date_range(start, end, freq=freq))


def get_entitlement_overflow_interval_week(absence):
    interval = generate_series_between_two_dates(absence.start, absence.end, freq='W-MON')

    w_start = get_week_start(absence.start)
    w_end = get_week_end(absence.end)
    w_interval = [w_start] + list(interval) + [w_end]

    for i in range(0, len(w_interval) - 1):
        w_start = w_interval[i]
        w_end = w_interval[i + 1]
        qs = get_overlap_absences(start=w_start,employee=absence.submitted_for,
                                  end=w_end, status=ABSENCE_STATUS_CHOICES.APPROVED)
        qs = qs.exclude(pk=absence.pk)

        absences_consumed = get_consumed_absence(qs)
        start = w_start
        end = w_end

        if w_start < absence.start:
            start = absence.start
        if w_end > absence.end:
            end = absence.end

        duration = get_leaves_duration(start, end)

        if absences_consumed + duration >absence.absence_type.entitlement:
            f_start = formatted_date(w_start)
            f_end = formatted_date(w_end + dt.timedelta(days=-1))
            return dict(start=f_start, end=f_end, consumed=absences_consumed)

    return None

def get_entitlement_overflow_interval_month(absence):
    interval = generate_series_between_two_dates(absence.start, absence.end, freq='MS')


    m_start = absence.start.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    m_end = absence.end.replace(day=1, hour=0, minute=0, second=0, microsecond=0)+ dt.timedelta(days=32)
    m_end = m_end.replace(day=1)
    m_interval = [m_start] + list(interval) + [m_end]

    for i in range(0, len(m_interval) - 1):
        m_start = m_interval[i]
        m_end = m_interval[i + 1]
        qs = get_overlap_absences(start=m_start,employee=absence.submitted_for,
                                  end=m_end, status=ABSENCE_STATUS_CHOICES.APPROVED)
        qs = qs.exclude(pk=absence.pk)

        absences_consumed = get_consumed_absence(qs)
        start = m_start
        end = m_end

        if m_start < absence.start:
            start = absence.start
        if m_end > absence.end:
            end = absence.end

        duration = get_leaves_duration(start, end)

        if absences_consumed + duration >absence.absence_type.entitlement:
            f_start = formatted_date(m_start)
            f_end = formatted_date(m_end + dt.timedelta(days=-1))
            return dict(start=f_start, end=f_end, consumed=absences_consumed)

    return None



def get_entitlement_overflow_interval_year(absence):
    interval = generate_series_between_two_dates(absence.start, absence.end, freq='A')


    y_start = absence.start.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    y_end = absence.end.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)+ dt.timedelta(days=370)
    y_end = y_end.replace(month=1, day=1) - dt.timedelta(days=1)
    m_interval = [y_start] + list(interval) + [y_end]

    for i in range(0, len(m_interval) - 1):
        y_start = m_interval[i]
        y_end = m_interval[i + 1]
        qs = get_overlap_absences(start=y_start,employee=absence.submitted_for,
                                  end=y_end,status=ABSENCE_STATUS_CHOICES.APPROVED)
        qs = qs.exclude(pk=absence.pk)

        absences_consumed = get_consumed_absence(qs)
        start = y_start
        end = y_end

        if y_start < absence.start:
            start = absence.start
        if y_end > absence.end:
            end = absence.end

        duration = get_leaves_duration(start, end)

        if absences_consumed + duration >absence.absence_type.entitlement:
            f_start = formatted_date(y_start)
            f_end = formatted_date(y_end)
            return dict(start=f_start, end=f_end, consumed=absences_consumed)

    return None


def notify_subordinates_about_general_absence(instance):
    if instance.status == ABSENCE_STATUS_CHOICES.APPROVED:
        audience = Employee.objects.filter(company=instance.company)
        departments = instance.department.all()
        if departments.exists():
            audience = audience.filter(department__in=departments)

        audience_ids = audience.all().values_list('id', flat=True)
        push_notification(GENERAL_ABSENCE_CREATED, audience_ids, instance)

        email = emails.GeneralAbsencePublished(absence=instance, iterable=audience)
        email.send()


def get_overlap_absences(start, end, employee, status=None):
    start = start + dt.timedelta(seconds=1)
    end = end + dt.timedelta(seconds=-1)

    queryset = EmployeeAbsence.objects.filter(company=employee.company, submitted_for=employee)

    queryset = queryset.filter(
        Q(end__range=(start, end)) |
        Q(start__range=(start, end)) |
        Q(start__lte=start, end__gte=end)
    )

    if status is not None:
        queryset = queryset.filter(status=status)

    queryset = queryset.select_related('absence_type')

    return queryset

def get_general_absence_qs_filter(user):
    q = Q(company=user.company)

    if user.is_manager_admin_or_manager() and user.active_department is not None:
        q = q & Q(department=user.active_department)
    if user.is_staff_():
        q = q & Q(department=user.department)
    if user.is_employee():
        q = q & Q(department=user.department, status=ABSENCE_STATUS_CHOICES.APPROVED)

    return q

def get_employee_absences_events_queryset(profile, user):
    qs = EmployeeAbsence.get_event_queryset(submitted_for=profile)
    qs = qs.filter(company=user.company, status=ABSENCE_STATUS_CHOICES.APPROVED)

    if user.is_employee():
        qs = qs.filter(submitted_for=user)

    return qs

def get_general_absences_events_queryset(profile, user):
    q = get_general_absence_qs_filter(profile)
    return GeneralAbsence.get_event_queryset(q).filter(deleted_at__isnull=True)


def create_shift_absence(employee_shift, request_user):
    absence_type = EmployeeAbsenceType.objects.filter(duration=DURATION.SHIFT, company=request_user.company).first()
    return EmployeeAbsence.objects.create(absence_type=absence_type,
                                          subject=_('ABSENT_FROM_SHIFT'),
                                          submitted_for=employee_shift.employee,
                                          submitted_by=request_user,
                                          submitted_to=request_user,
                                          status=ABSENCE_STATUS_CHOICES.APPROVED,
                                          start=employee_shift.shift.start,
                                          end=employee_shift.shift.end,
                                          company=request_user.company)
