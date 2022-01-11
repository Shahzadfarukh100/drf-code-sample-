from django.conf import settings
from django.utils.translation import ugettext_noop as _noop
from django.utils.translation import ugettext_lazy as _

from constants.db import ABSENCE_STATUS_CHOICES
from helpers.formatting import formatted_date
from mail.email import Email, MakeEmail


class AbsenceSubmittedManager(Email):
    subject = _noop('ABSENCE_SUBMITTED_TO_MANAGER')
    subject_1 = _('ABSENCE_SUBMITTED_TO_MANAGER')
    template = 'ABSENCE_SUBMITTED_MANAGER'

    def __init__(self, absence):
        self.absence = absence
        super().__init__(to=absence.submitted_to.email)

    def get_context(self):
        context = super().get_context()
        context['link'] = f'{settings.FRONT_END_APP_URL}/absences/{self.absence.id}/view'
        context['submitted_to_first_name'] = self.absence.submitted_to.first_name
        context['submitted_for_full_name'] = self.absence.submitted_for.get_full_name()
        context['language'] = self.absence.submitted_to.language
        return context


class AbsenceSubmittedForUser(Email):
    subject = _noop('ABSENCE_SUBMITTED_FOR_USER')
    subject_1 = _('ABSENCE_SUBMITTED_FOR_USER')
    template = 'ABSENCE_SUBMITTED_FOR_USER'

    def __init__(self, absence):
        self.absence = absence
        super().__init__(to=absence.submitted_for.email)

    def get_context(self):
        context = super().get_context()
        context['link'] = f'{settings.FRONT_END_APP_URL}/absences/{self.absence.id}/view'
        context['submitted_for_first_name'] = self.absence.submitted_for.first_name
        context['submitted_by_full_name'] = self.absence.submitted_by.get_full_name()
        context['language'] = self.absence.submitted_for.language
        return context


class AbsenceUpdated(Email):
    subject = _noop('ABSENCE_STATUS_HAS_BEEN_UPDATED')
    subject_1 = _('ABSENCE_STATUS_HAS_BEEN_UPDATED')
    template = 'ABSENCE_STATUS_UPDATED'

    def __init__(self, absence, comment):
        self.absence = absence
        self.comment = comment
        super().__init__(to=absence.submitted_for.email)

    def get_context(self):
        context = super().get_context()
        context['link'] = f'{settings.FRONT_END_APP_URL}/absences/{self.absence.id}/view'
        context['update_by_full_name'] = self.comment.commented_by.get_full_name()
        context['submitted_for_first_name'] = self.absence.submitted_for.first_name
        context['submitted_to_full_name'] = self.absence.submitted_to.get_full_name() if self.absence.submitted_to is not None else ''
        context['status'] = str(ABSENCE_STATUS_CHOICES[self.absence.status])
        context['language'] = self.absence.submitted_for.language
        return context


class GeneralAbsencePublished(MakeEmail):
    subject = _noop('ABSENCE_PUBLISHED_EMAIL_SUBJECT')
    subject_1 = _('ABSENCE_PUBLISHED_EMAIL_SUBJECT')
    template = 'GENERAL_ABSENCE_PUBLISHED'

    def __init__(self, *args, absence, **kwargs):
        self.instance = absence
        super().__init__(*args, **kwargs)

    def get_context(self):
        context = super().get_context()
        context['duration'] = (self.instance.end - self.instance.start).days + 1
        context['link'] = f'{settings.FRONT_END_APP_URL}/absences?id={self.instance.id}'
        context['start_date'] = str(formatted_date(self.instance.start.date()))
        context['end_date'] = str(formatted_date(self.instance.end.date()))
        context['manager_name'] = self.instance.submitted_by.get_full_name()

        return context

    def make_context(self, item):
        context = super().make_context(item)
        context['first_name'] = item.first_name
        context['language'] = item.language
        return context

    def make_to(self, item):
        return item.email
