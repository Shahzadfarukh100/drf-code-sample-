from django.apps import AppConfig


class AbsenceConfig(AppConfig):
    name = 'absence'

    def ready(self):
        import absence.receivers
        absence.receivers.connect()
