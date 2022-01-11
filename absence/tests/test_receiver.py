from unittest.mock import patch

from django.test import TestCase
from model_bakery import baker

from absence.receivers import _account_created_receiver
from account.models import Company


class TestReceiver(TestCase):

    @patch('absence.receivers.create_default_absence_types')
    def test_account_created_receiver(self, default_absence_types):
        company = baker.make(Company)
        _account_created_receiver(**dict(company=company))
        default_absence_types.assert_called_once_with(company)
