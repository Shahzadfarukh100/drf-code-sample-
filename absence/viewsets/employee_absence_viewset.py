from django.db.models import Prefetch
from django.db.models.query_utils import Q
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, status, decorators
from rest_framework.response import Response

from absence.filters import EmployeeAbsenceFilter
from absence.models import EmployeeAbsence, EmployeeAbsenceComment
from absence.modules.dataset_generator import EmployeeAbsenceListViewDataSetGenerator
from absence.permissions import EmployeeAbsencePermission
from absence.serializers.employee_absence_serializer import (
    EmployeeAbsenceListSerializer, EmployeeAbsenceCreateSerializer,
    EmployeeAbsenceStatusUpdateSerializer,
)
from absence.utils import get_already_taken_leaves
from account.models import Employee
from constants.db import ABSENCE_STATUS_CHOICES
from core.filters import TrigramSearchFilterBackend
from core.mixins import GetSerializerMixin, QuerySetMixin, ExportMixin
from core.utils import check_users_access
from history.mixins import ModelHistoryMixin


class EmployeeAbsenceViewSet(GetSerializerMixin,
                             ModelHistoryMixin,
                             QuerySetMixin,
                             ExportMixin,
                             viewsets.ModelViewSet):
    permission_classes = [EmployeeAbsencePermission]
    exportGenerator = EmployeeAbsenceListViewDataSetGenerator

    search_fields = ('subject',)
    filter_class = EmployeeAbsenceFilter
    filter_backends = [TrigramSearchFilterBackend, DjangoFilterBackend]

    serializer_class = EmployeeAbsenceListSerializer
    serializer_action_classes = {
        'create': EmployeeAbsenceCreateSerializer,
        'status': EmployeeAbsenceStatusUpdateSerializer,
        'user_absences': EmployeeAbsenceListSerializer
    }

    def get_all_queryset(self):
        request_user = self.get_request_user()
        qs = EmployeeAbsence.objects.filter(company=request_user.company)
        qs = qs.select_related('submitted_by', 'submitted_for','submitted_to', 'absence_type')
        _qs = EmployeeAbsenceComment.objects.filter().select_related('commented_by', 'commented_by__department')
        qs = qs.prefetch_related(Prefetch('employeeabsencecomment_set', queryset=_qs))

        if request_user.is_employee():
            qs = qs.filter(submitted_for=request_user)
        if request_user.is_staff_():
            qs = qs.filter(Q(submitted_to=request_user) | Q(submitted_for=request_user))
        return qs

    def get_user_absences_queryset(self):
        request_user = self.get_request_user()
        employee_id = self.request.query_params.get('employee_id')
        qs = EmployeeAbsence.objects.none()

        employee = Employee.objects.filter(pk=employee_id).first()

        if employee is not None and check_users_access(employee, request_user):
            qs = EmployeeAbsence.objects.filter(company=employee.company, submitted_for=employee)
        return qs


    @decorators.action(methods=['get'], detail=False)
    def requests(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

    @decorators.action(methods=['get'], detail=False)
    def user_absences(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        absence = self.get_object()
        absence.delete()
        return Response({'success': True}, status=status.HTTP_204_NO_CONTENT)

    @decorators.action(['put'], detail=True)
    def status(self, request, *args, **kwargs):
        return self.update(request, *args, **kwargs)

    @decorators.action(methods=['get'], detail=False)
    def export(self, *_args, **_kwargs):
        return self.export_data()

    @decorators.action(methods=['get'], detail=True)
    def detail_history(self, _request, *_args, **_kwargs):
        absence = self.get_object()
        leaves_taken = get_already_taken_leaves(absence, status=ABSENCE_STATUS_CHOICES.APPROVED)
        serializer = self.get_serializer(absence)
        history_data = {'already_taken': leaves_taken,
                        'current_allowance': absence.absence_type.entitlement - leaves_taken}
        data = {**serializer.data, **history_data}
        return Response(data)
