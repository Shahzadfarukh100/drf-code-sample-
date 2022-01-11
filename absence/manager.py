from django.db import models


class EmployeeAbsencesTypeManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True)

    def get_all_object(self):
        return super().get_queryset()

    def get_archive_object(self):
        return super().get_queryset().filter(deleted_at__isnull=False)