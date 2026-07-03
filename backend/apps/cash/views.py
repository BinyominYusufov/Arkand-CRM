from django.utils import timezone
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from apps.core import rbac
from apps.core.permissions import (
    CanManageCashRegisters,
    CashSection,
    IsCashRegisterMember,
)

from . import selectors, services
from .models import CashOperation, CashRegister
from .serializers import (
    CashOperationCreateSerializer,
    CashOperationSerializer,
    CashRegisterSerializer,
)


def _attach_overview(register: CashRegister) -> CashRegister:
    now = timezone.localtime()
    data = selectors.register_overview(register, year=now.year, month=now.month)
    for field in ("balance", "month_turnover", "limit_utilization", "over_limit"):
        setattr(register, field, data[field])
    return register


class CashRegisterViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """Кассы (КАС-01…04): кассир видит только свои — изоляция в selectors."""

    serializer_class = CashRegisterSerializer
    permission_classes = [CanManageCashRegisters, IsCashRegisterMember]
    filterset_fields = ["business"]
    pagination_class = None

    def get_queryset(self):
        return selectors.registers_for_user(self.request.user)

    def list(self, request, *args, **kwargs):
        registers = [
            _attach_overview(r) for r in self.filter_queryset(self.get_queryset())
        ]
        return Response(CashRegisterSerializer(registers, many=True).data)

    def retrieve(self, request, *args, **kwargs):
        register = _attach_overview(self.get_object())
        return Response(CashRegisterSerializer(register).data)


class CashOperationViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """Операции касс (КАС-02); создание — через сервис с лимитом (КАС-03)."""

    serializer_class = CashOperationSerializer
    permission_classes = [CashSection]
    filterset_fields = ["register", "direction", "method"]
    ordering_fields = ["occurred_at", "amount"]

    def get_queryset(self):
        return selectors.operations_for_user(self.request.user)

    def create(self, request):
        ser = CashOperationCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        register = ser.validated_data["register"]
        # Изоляция КАС-04: писать можно только в доступную кассу.
        if not selectors.registers_for_user(request.user).filter(pk=register.pk).exists():
            raise PermissionDenied("Чужая касса недоступна")
        op = services.create_cash_operation(
            request.user,
            register=register,
            direction=ser.validated_data["direction"],
            method=ser.validated_data["method"],
            amount=ser.validated_data["amount"],
            occurred_at=ser.validated_data.get("occurred_at"),
            note=ser.validated_data.get("note", ""),
        )
        return Response(CashOperationSerializer(op).data, status=status.HTTP_201_CREATED)

    def destroy(self, request, pk=None):
        op = self.get_object()  # queryset уже изолирован
        if not rbac.user_has_perm(request.user, rbac.PERM_CASH_MANAGE):
            raise PermissionDenied("Удалять операции может только финотдел")
        services.soft_delete_cash_operation(request.user, operation_id=op.id)
        return Response(status=status.HTTP_204_NO_CONTENT)
