from rest_framework.routers import DefaultRouter

from .views import EmployeeViewSet, PayrollRunViewSet, SalarySchemeViewSet

router = DefaultRouter()
router.register("employees", EmployeeViewSet, basename="employee")
router.register("schemes", SalarySchemeViewSet, basename="salary-scheme")
router.register("runs", PayrollRunViewSet, basename="payroll-run")

urlpatterns = router.urls
