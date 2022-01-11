from rest_framework import routers

from .viewsets.absence_type_viewset import EmployeeAbsenceTypeViewSet
from .viewsets.employee_absence_viewset import EmployeeAbsenceViewSet
from .viewsets.general_absence_viewset import GeneralAbsenceViewSet

router = routers.SimpleRouter()
router.register(r'absence', EmployeeAbsenceViewSet, base_name='absence')
router.register(r'absence_type', EmployeeAbsenceTypeViewSet, base_name='absence_type')
router.register(r'general_absence', GeneralAbsenceViewSet, base_name='general_absence')

urlpatterns = router.urls
