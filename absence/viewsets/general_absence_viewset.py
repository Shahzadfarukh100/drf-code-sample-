from django.db.models import Q
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import decorators
from rest_framework import viewsets

from absence.filters import GeneralAbsenceFilter
from absence.models import GeneralAbsence
from absence.modules.dataset_generator import GeneralAbsenceListViewDataSetGenerator
from absence.permissions import GeneralAbsencePermissions
from absence.serializers.general_absence_serializer import (GeneralAbsenceSerializer,
                                                            GeneralAbsenceCreateSerializer,
                                                            GeneralAbsenceUpdateSerializer)
from absence.utils import get_general_absence_qs_filter
from constants.db import ABSENCE_STATUS_CHOICES
from core.filters import TrigramSearchFilterBackend
from core.mixins import QuerySetMixin, GetSerializerMixin, ArchivedActionMixin, ExportMixin
from history.mixins import ModelHistoryMixin


class GeneralAbsenceViewSet(QuerySetMixin,
                            GetSerializerMixin,
                            viewsets.ModelViewSet,
                            ArchivedActionMixin,
                            ExportMixin,
                            ModelHistoryMixin):
    serializer_class = GeneralAbsenceSerializer
    permission_classes = [GeneralAbsencePermissions]
    exportGenerator = GeneralAbsenceListViewDataSetGenerator
    serializer_action_classes = {
        'create': GeneralAbsenceCreateSerializer,
        'update': GeneralAbsenceUpdateSerializer,
    }

    search_fields = ('subject',)
    filter_class = GeneralAbsenceFilter
    filter_backends = [TrigramSearchFilterBackend, DjangoFilterBackend]

    @staticmethod
    def get_all_queryset():
        return GeneralAbsence.objects.filter(deleted_at__isnull=True)

    @staticmethod
    def get_restore_queryset():
        return GeneralAbsence.objects.filter(deleted_at__isnull=False)

    @staticmethod
    def get_archived_queryset():
        return GeneralAbsence.objects.filter(deleted_at__isnull=False)

    @staticmethod
    def get_export_archived_queryset():
        return GeneralAbsence.objects.filter(deleted_at__isnull=False)

    def filter_query(self):
        user = self.get_request_user()
        return get_general_absence_qs_filter(user)

    @decorators.action(methods=['get'], detail=False)
    def export(self, *_args, **_kwargs):
        return self.export_data()

    @decorators.action(methods=['get'], detail=False)
    def export_archived(self, *args, **kwargs):
        return self.export(*args, **kwargs)

    def perform_destroy(self, instance):
        instance.deleted_at = timezone.now()
        instance.save()