from django.dispatch import Signal

general_absence_created = Signal(providing_args=['instance'])
absence_created = Signal(providing_args=['instance'])
