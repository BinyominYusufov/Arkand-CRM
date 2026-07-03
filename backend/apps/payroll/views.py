from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.core.permissions import PayrollSection

from . import services
from .models import Employee, PayrollRun, SalaryScheme
from .serializers import (
    EmployeeSerializer,
    PayrollRunDetailSerializer,
    PayrollRunSerializer,
    RunPayrollSerializer,
    SalarySchemeSerializer,
)


class EmployeeViewSet(viewsets.ModelViewSet):
    """Сотрудники (ЗРП-02). Финотдел — CRUD, владельцы — чтение."""

    queryset = Employee.objects.select_related("business").all()
    serializer_class = EmployeeSerializer
    permission_classes = [PayrollSection]
    filterset_fields = ["business", "salary_type", "is_salesperson", "is_active"]
    search_fields = ["full_name", "position"]

    def perform_destroy(self, instance):
        # Сотрудников не удаляем физически — деактивируем.
        instance.is_active = False
        instance.save(update_fields=["is_active"])


class SalarySchemeViewSet(viewsets.ModelViewSet):
    """Схемы зарплаты (ЗРП-03…05) — data-driven, конфиг в JSON."""

    queryset = SalaryScheme.objects.select_related("employee").all()
    serializer_class = SalarySchemeSerializer
    permission_classes = [PayrollSection]
    filterset_fields = ["employee", "scheme_type", "is_active"]


class PayrollRunViewSet(
    mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet
):
    """Расчёты зарплаты: создание = запуск расчёта (синхронно, в сервисе)."""

    permission_classes = [PayrollSection]
    filterset_fields = ["year", "month", "status"]

    def get_queryset(self):
        return PayrollRun.objects.prefetch_related(
            "items", "items__employee", "items__employee__business"
        ).all()

    def get_serializer_class(self):
        if self.action == "retrieve":
            return PayrollRunDetailSerializer
        return PayrollRunSerializer

    def create(self, request):
        ser = RunPayrollSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        run = services.run_payroll(
            request.user,
            year=ser.validated_data["year"],
            month=ser.validated_data["month"],
            inputs=ser.validated_data.get("inputs") or {},
        )
        return Response(
            PayrollRunDetailSerializer(run).data, status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=["post"])
    def finalize(self, request, pk=None):
        run = services.finalize_run(request.user, run_id=int(pk))
        return Response(PayrollRunSerializer(run).data)
