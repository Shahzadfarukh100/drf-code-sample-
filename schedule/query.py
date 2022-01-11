from django.db.models import Q

from constants.db import SCHEDULE_STATUS_CHOICES
from schedule.models import Schedule


class ScheduleQuerySet(object):

    def __init__(self, user):
        self.user = user
        self.qs = Schedule.objects.all()

    def default_queryset(self):
        self.qs = self.qs.filter(department__company=self.user.company)
        self.qs = self.qs.select_related('department')

    def get_queryset(self):
        self.default_queryset()
        self.queryset_for_manager_admin_or_manager()
        self.queryset_for_staff()
        self.queryset_for_employee()
        self.queryset_sorting()
        return self.qs

    def queryset_for_manager_admin_or_manager(self):
        if self.user.is_manager_admin_or_manager() and self.has_user_active_department():
            self.queryset_for_user_active_department()


    def queryset_for_staff(self):
        if self.user.is_staff_():
            self.queryset_for_user_department()

    def queryset_for_employee(self):
        if self.user.is_employee():
            self.queryset_for_user_department()
            self.qs = self.qs.filter(status=SCHEDULE_STATUS_CHOICES.PUBLISHED)
            self.qs = self.qs.filter(end__gte=self.user.created)

    def queryset_for_user_department(self):
        schedule_ids = self.get_user_involved_schedules()
        self.qs = self.qs.filter(Q(department=self.user.department) | Q(id__in=schedule_ids))

    def get_user_involved_schedules(self):
        q =  self.user.allocated_in.filter(schedule__status=SCHEDULE_STATUS_CHOICES.PUBLISHED)
        return q.values_list('schedule_id', flat=True)

    def queryset_for_user_active_department(self):
        self.qs = self.qs.filter(department=self.user.active_department)

    def queryset_sorting(self):
        self.qs = self.qs.order_by('-start', 'department__name')

    def has_user_active_department(self):
        return self.user.active_department is not None
