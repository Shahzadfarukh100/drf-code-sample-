import datetime as dt
import logging

from django.db import transaction
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, mixins, status, decorators, permissions
from rest_framework.response import Response

from account.models import Employee
from conf.settings import ENVIRONMENT
from constants.db import SCHEDULE_STATUS_CHOICES
from core.mixins import GetSerializerMixin, QuerySetMixin, ExportMixin
from core.tasks.schedule import (
    task_collecting_preferences_tasks,
    task_publishing_tasks
)
from history.mixins import ModelHistoryMixin
from r_api.utils import delete_task_to_optimization_management
from schedule.filters import ScheduleListFilter
from schedule.models import Schedule
from schedule.models import ScheduleFeedback
from schedule.modules.dataset_generator import ScheduleListViewDataSetGenerator
from schedule.permissions import SchedulePermission
from schedule.query import ScheduleQuerySet
from schedule.serializers import (
    ScheduleListSerializer, ScheduleFeedbackListSerializer, ScheduleRetrieveSerializer,
    ScheduleCreateSerializer,
    ScheduleFeedbackCreateSerializer)
from schedule.utils import get_schedule_feedback_stats, send_email_on_collect_preferences_schedule, \
    send_email_on_publish_schedule
from shift.models import Shift
from shift.serializers import ShiftAsEventSerializer
from shift.utils import get_shift_queryset_for_schedule

logger = logging.getLogger(__name__)



class ScheduleViewSet(
    GetSerializerMixin,
    ExportMixin,
    ModelHistoryMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [SchedulePermission]
    exportGenerator = ScheduleListViewDataSetGenerator
    filter_class = ScheduleListFilter
    filter_backends = [DjangoFilterBackend, ]


    serializer_action_classes = {
        'events': ShiftAsEventSerializer,
        'list': ScheduleListSerializer,
        'retrieve': ScheduleRetrieveSerializer,
        'create': ScheduleCreateSerializer,
    }

    def get_request_user(self):
        return self.request.user

    def get_queryset(self):
        user = self.get_request_user()
        queryset = ScheduleQuerySet(user)
        return queryset.get_queryset()

    @decorators.action(detail=True, methods=['post'])
    def collect_preferences(self, request, *_args, **_kwargs):
        instance = self.get_object()

        instance.status = SCHEDULE_STATUS_CHOICES.COLLECTING_PREFERENCE
        instance.save()

        instance.make_timestamp()
        task = task_collecting_preferences_tasks.delay(instance.pk)

        send_email_on_collect_preferences_schedule(request.user, instance)

        return Response({'task_id': task.task_id}, status=status.HTTP_202_ACCEPTED)

    @decorators.action(detail=True, methods=['post'])
    def request_schedule(self, _request, *_args, **_kwargs):
        instance = self.get_object()

        instance.status = SCHEDULE_STATUS_CHOICES.PRODUCING_SCHEDULE
        instance.save()
        instance.make_timestamp()

        return Response({'success': True})

    @decorators.action(detail=True, methods=['post'])
    def publish(self, request, *_args, **_kwargs):
        instance = self.get_object()

        instance.status = SCHEDULE_STATUS_CHOICES.PUBLISHED
        instance.save()

        instance.make_timestamp()
        task = task_publishing_tasks.delay(instance.pk)

        send_email_on_publish_schedule(request.user, instance)

        return Response({'task_id': task.task_id}, status=status.HTTP_202_ACCEPTED)

    @decorators.action(detail=True, methods=['put'])
    def stop_collecting_preferences(self, *_args, **_kwargs):
        instance = self.get_object()
        if instance.status == SCHEDULE_STATUS_CHOICES.COLLECTING_PREFERENCE:
            instance.status = SCHEDULE_STATUS_CHOICES.PRODUCING_SCHEDULE
            instance.save()
        return Response({'success': True})

    @decorators.action(methods=['get'], detail=False)
    def export(self, *_args, **_kwargs):
        return self.export_data()

    @decorators.action(methods=['get'], detail=True)
    def events(self, request, *_args, **_kwargs):
        schedule = self.get_object()
        start = request.query_params.get('start')
        end = request.query_params.get('end')

        start = dt.datetime.strptime(start, '%Y-%m-%d') - dt.timedelta(days=1)
        end = dt.datetime.strptime(end, '%Y-%m-%d') + dt.timedelta(days=1)

        user = self.get_request_user()
        qs = get_shift_queryset_for_schedule(user, schedule, start, end)

        serializer = ShiftAsEventSerializer(qs, many=True)
        return Response(serializer.data)

    def perform_destroy(self, instance):
        delete_task_to_optimization_management(instance.id)
        super().perform_destroy(instance)


class ScheduleFeedbackViewSet(mixins.CreateModelMixin,
                              mixins.ListModelMixin,
                              ModelHistoryMixin,
                              GetSerializerMixin,
                              QuerySetMixin,
                              viewsets.GenericViewSet):


    serializer_action_classes = {
        'list': ScheduleFeedbackListSerializer,
        'create': ScheduleFeedbackCreateSerializer,
    }

    def get_query_params(self):
        return self.request.query_params

    def get_request_user(self):
        return self.request.user

    def get_all_queryset(self):
        instance = self.get_schedule()
        qs = instance.employee_feedback.all()
        qs = qs.select_related('employee')
        return qs.order_by('-created')

    def get_schedule_queryset(self):
        user = self.get_request_user()
        queryset = ScheduleQuerySet(user)
        return queryset.get_queryset()

    def get_schedule(self):
        query_params = self.get_query_params()
        schedule = query_params.get('schedule', None)

        qs = self.get_schedule_queryset()
        qs = qs.filter(pk=schedule, status=SCHEDULE_STATUS_CHOICES.PUBLISHED)

        return qs.first()


    def get_list_queryset(self):
        user = self.get_request_user()
        if user.is_employee():
            return ScheduleFeedback.objects.none()
        return self.get_all_queryset().filter(share_with_manager=True)

    @decorators.action(detail=False, methods=['get'])
    def feedback_stats(self, *_args, **_kwargs):
        qs = self.get_all_queryset()
        stats = get_schedule_feedback_stats(qs)
        return Response(stats)

    @decorators.action(detail=False, methods=['get'])
    def feedback_given(self, request, *_args, **_kwargs):
        feedback_given = self.get_queryset().filter(employee=request.user).exists()
        return Response({'feedback_given': feedback_given})


class ScheduleOptimizationViewSet(mixins.CreateModelMixin,
                           viewsets.GenericViewSet):
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):

        if ENVIRONMENT == 'production':
            return Response({'success': True})


        shifts = request.data

        with transaction.atomic():
            for shift in shifts:
                for employee in shifts[shift]:
                    try:
                        Shift.objects.get(id=shift).employees_allocated.add(Employee.objects.get(id=employee))
                    except Exception as e:
                        logger.error('Error in Optimization allocation', exc_info=e)

            try:
                shift = list(shifts.keys())[0]
                schedule = Schedule.objects.get(id=Shift.objects.get(id=shift).schedule_id)

                schedule.status = SCHEDULE_STATUS_CHOICES.REVIEWING_SCHEDULE
                schedule.save()
                schedule.make_timestamp()

            except Exception as e:
                logger.error('Error in Optimization allocation', exc_info=e)

        return Response({'success': True})