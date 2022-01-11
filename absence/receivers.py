from absence.signals import general_absence_created, absence_created
from absence.utils import create_default_absence_types, notify_subordinates_about_general_absence, \
    notify_manger_about_absence_submission, notify_user_about_absence_submission_and_approved
from account.signals import account_created


def _account_created_receiver(**kwargs):
    create_default_absence_types(kwargs['company'])


def _general_absence_created_receiver(**kwargs):
    notify_subordinates_about_general_absence(kwargs['instance'])


def _absence_created_receiver(**kwargs):
    instance = kwargs['instance']

    if instance.submitted_by==instance.submitted_for:
        notify_manger_about_absence_submission(instance)

    if instance.submitted_by==instance.submitted_to:
        notify_user_about_absence_submission_and_approved(instance)


def connect():
    account_created.connect(_account_created_receiver, dispatch_uid='absence_account_created_receiver')
    general_absence_created.connect(_general_absence_created_receiver, dispatch_uid='general_absence_created_receiver')
    absence_created.connect(_absence_created_receiver, dispatch_uid='absence_created_receiver')
