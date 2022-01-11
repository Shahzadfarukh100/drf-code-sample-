from rest_framework import routers

from .viewsets import ScheduleViewSet, ScheduleFeedbackViewSet, ScheduleOptimizationViewSet

router = routers.SimpleRouter()
router.register(r'schedule', ScheduleViewSet, base_name='schedule')
router.register(r'schedule_feedback', ScheduleFeedbackViewSet, base_name='schedule_feedback')
router.register(r'schedule_optimization', ScheduleOptimizationViewSet, base_name='schedule_optimization')

urlpatterns = router.urls
