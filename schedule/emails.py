from django.conf import settings
from django.utils.translation import ugettext_noop as _noop
from django.utils.translation import ugettext_lazy as _


from helpers.formatting import formatted_date, local_datetime, formatted_datetime
from mail.email import MakeEmail


class CollectPreferencesEmail(MakeEmail):
    subject = _noop('SUBMIT_YOUR_PREFERENCES')
    subject_t = _('SUBMIT_YOUR_PREFERENCES')
    template = 'COLLECT_PREFERENCES_EMAIL'

    def __init__(self, schedule, iterable, *args):
        self.schedule = schedule
        super().__init__(*args, iterable=iterable)

    def make_context(self, item):
        context = super().make_context(item)
        context['first_name'] = item.first_name
        context['language'] = item.language
        return context

    def make_to(self, item):
        return item.email

    def get_context(self):
        context = super().get_context()
        context['start_date'] = str(formatted_date(self.schedule.start))
        context['end_date'] = str(formatted_date(self.schedule.end))
        context['deadline'] = str(formatted_datetime(local_datetime(self.schedule.preferences_deadline)))
        context['link'] = f'{settings.FRONT_END_APP_URL}/preferences/schedule/{self.schedule.id}'
        return context


class SchedulePublishedEmail(CollectPreferencesEmail):
    subject = _noop('A_NEW_SCHEDULE_HAS_BEEN_PUBLISHED')
    subject_t = _('A_NEW_SCHEDULE_HAS_BEEN_PUBLISHED')
    template = 'SCHEDULE_PUBLISHED_EMAIL'

    def get_context(self):
        context = super().get_context()
        context.pop('deadline', None)
        context['link'] = f'{settings.FRONT_END_APP_URL}/schedule/{self.schedule.id}'
        return context


class ShiftNotification(MakeEmail):
    def __init__(self, start, end):
        pass
