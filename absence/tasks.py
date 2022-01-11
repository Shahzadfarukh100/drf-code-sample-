# from celery import shared_task
#
# from absence.models import EmployeeAbsence
#
#
# @shared_task()
# def assign_absences_to_given_manager(employee_id, assign_absences_to):
#     EmployeeAbsence.objects.filter(
#         submitted_to_id=employee_id
#     ).update(
#         submitted_to_id=assign_absences_to
#     )
