import datetime as dt
import logging
from datetime import timedelta

from django.db.models import Max, Min
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from absence.utils import get_overlap_absences
from constants.db import ABSENCE_STATUS_CHOICES, DURATION
from employee_shift.utils import is_employee_shift_exist_for_employee
from helpers.formatting import formatted_date, formatted_datetime

logger = logging.getLogger(__name__)


class BaseAbsenceSerializer(serializers.ModelSerializer):


    @staticmethod
    def validate_overlap(data):
        start = data.get('start')
        end = data.get('end')
        submitted_for = data.get('submitted_for')
        absence_duration = data.get('absence_duration')
        qs = get_overlap_absences(start, end, submitted_for)
        if qs.exists():
            absence = qs.aggregate(latest_date=Max('end'), earliest_date=Min('start'))

            if absence_duration==DURATION.HOURLY:
                start = formatted_datetime(absence['earliest_date'])
                end = formatted_datetime(absence['latest_date'])
            else:
                start = formatted_date(absence['earliest_date'])
                end = formatted_date(absence['latest_date'] - dt.timedelta(seconds=1))

            error_message = _('ABSENCE_HAS_ALREADY_BEEN_APPLIED_IN_GIVEN_DATES_{start}_TO_{end}. '
                              'PLEASE_CHOOSE_A_NON-OVERLAPPING_TIME_INTERVAL'
                              .format(start=start, end=end))

            raise serializers.ValidationError(error_message)

    @staticmethod
    def validate_dates(data):
        start = data.get('start')
        end = data.get('end')
        if start > end:
            raise serializers.ValidationError(_('END_DATE_CAN_NOT_BE_A_DATE_BEFORE_START_DATE'))


    def set_employee_relations(self, data):
        request_user = self.get_request_user()
        data['submitted_by'] = request_user

        submitted_to = data.get('submitted_to') or None
        submitted_for = data.get('submitted_for') or None

        if submitted_for is None and submitted_to is not None:
            data['submitted_for'] = request_user

        if submitted_to is None and submitted_for is not None:
            data['submitted_to'] = request_user

        if not ((data['submitted_by'] == data['submitted_to']) or
                (data['submitted_by'] == data['submitted_for'])):
            logger.error('Something wrong in submitted_by or submitted_to or submitted_for', exc_info=data)


    @staticmethod
    def set_end_date(data):
        end = data.get('end')
        absence_type = data.get('absence_type')

        if not absence_type.hourly:
            end = end.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)

        data['end'] = end

    @staticmethod
    def validate_submit_before(data):
        start = data.get('start')
        absence_type = data.get('absence_type')
        if absence_type.submit_before_days != 0:

            days = (start - timezone.now()).days
            if absence_type.submit_before_days > days:
                raise serializers.ValidationError(
                    _('ABSENCE_SHOULD_SUBMITTED_BEFORE_{days}_DAYS').format(days=absence_type.submit_before_days)
                )

    @staticmethod
    def validate_shift_overlap(data):
        start = data.get('start')
        end = data.get('end')

        employee = data.get('submitted_for', None) or None
        ignore_shift_overlap = data.get('ignore_shift_overlap', False)

        if not ignore_shift_overlap and is_employee_shift_exist_for_employee(employee, start, end):
            raise serializers.ValidationError(
                {'ignore_shift_overlap':
                     _('EMPLOYEE_SHIFT_EXIST_FOR_THIS_DURATION.ARE_YOU_STILL_WANT_TO_SUBMIT_ABSENCE')})

    def set_status(self, data):
        user = self.get_request_user()
        submitted_to = data.get('submitted_to') or None
        submitted_by = data.get('submitted_by') or None

        status = ABSENCE_STATUS_CHOICES.PENDING
        if not user.is_employee() and submitted_by == submitted_to and submitted_by is not None:
            status = ABSENCE_STATUS_CHOICES.APPROVED
        data['status'] = status

    @staticmethod
    def set_company(data):
        submitted_for = data.get('submitted_for') or None
        data['company'] = submitted_for.company


    def validate_submitted_to(self, submitted_to):
        request_user = self.get_request_user()

        if submitted_to is not None and request_user.is_employee() and submitted_to.is_employee():
            raise serializers.ValidationError(_('EMPLOYEE_TO_SUBMIT_ABSENCE_NOT_FOUND'))
        return submitted_to

    def get_request_user(self):
        return self.context.get('request').user