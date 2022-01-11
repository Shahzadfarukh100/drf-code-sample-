from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import decorators
from rest_framework import viewsets
from rest_framework.response import Response

from absence.filters import EmployeeAbsenceTypeFilter
from absence.models import EmployeeAbsenceType
from absence.modules.dataset_generator import AbsenceTypeListViewDataSetGenerator
from absence.permissions import EmployeeAbsenceTypePermission
from absence.serializers.absence_type_serializer import (
    EmployeeAbsenceTypeSerializer
)
from constants.db import TODO_TYPE_CHOICES, DURATION
from core.filters import TrigramSearchFilterBackend
from core.mixins import QuerySetMixin, ArchivedActionMixin, ExportMixin
from history.mixins import ModelHistoryMixin
from todo.models import Todo


class EmployeeAbsenceTypeViewSet(ModelHistoryMixin,
                                 QuerySetMixin,
                                 ArchivedActionMixin,
                                 ExportMixin,
                                 viewsets.ModelViewSet,
                                 ):
    permission_classes = [EmployeeAbsenceTypePermission]
    filterset_class = EmployeeAbsenceTypeFilter
    serializer_class = EmployeeAbsenceTypeSerializer
    exportGenerator = AbsenceTypeListViewDataSetGenerator

    search_fields = ('name',)
    filter_backends = [TrigramSearchFilterBackend, DjangoFilterBackend]

    def get_all_queryset(self):
        user = self.get_request_user()
        return EmployeeAbsenceType.objects.filter(company=user.company).exclude(duration=DURATION.SHIFT)

    def get_inactive_queryset(self):
        user = self.get_request_user()
        return EmployeeAbsenceType.objects.get_archive_object().filter(company=user.company)

    def get_restore_queryset(self):
        return self.get_inactive_queryset()

    def get_archived_queryset(self):
        return self.get_inactive_queryset()

    def get_export_archived_queryset(self):
        return self.get_inactive_queryset()

    @decorators.action(methods=['get'], detail=False)
    def export(self, *_args, **_kwargs):
        return self.export_data()

    @decorators.action(methods=['get'], detail=False)
    def export_archived(self, *_args, **_kwargs):
        return self.export_data()

    @decorators.action(detail=False, methods=['post'])
    def mark_todo_complete(self, request, *_args, **_kwargs):
        todo = Todo.objects.filter(company=request.user.company, type=TODO_TYPE_CHOICES.CHECK_ABSENCE_TYPES).first()
        if todo is not None:
            todo.completed = True
            todo.save()
        return Response({})
