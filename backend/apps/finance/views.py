"""Тонкие вьюхи финансов: принять → вызвать сервис/селектор → отдать."""
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core import rbac
from apps.core.exceptions import NotFoundError
from apps.core.permissions import CanApproveFinance, FinanceSection

from . import selectors, services
from .filters import TransactionFilter
from .models import ExpenseCategory, Transaction
from .serializers import (
    ExpenseCategorySerializer,
    TransactionCreateSerializer,
    TransactionSerializer,
)


class ExpenseCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """Справочник категорий расходов (ФНС-02)."""

    queryset = ExpenseCategory.objects.all()
    serializer_class = ExpenseCategorySerializer
    permission_classes = [FinanceSection]
    pagination_class = None


class TransactionViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """Приходы/расходы (ФНС-01…03). Мутации — только через сервисы."""

    serializer_class = TransactionSerializer
    permission_classes = [FinanceSection]
    filterset_class = TransactionFilter
    ordering_fields = ["occurred_at", "amount", "created_at"]
    search_fields = ["note"]

    def get_queryset(self):
        return selectors.transactions_for_user(self.request.user)

    def create(self, request):
        ser = TransactionCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data
        common = dict(
            business=data["business"],
            amount=data["amount"],
            method=data["method"],
            occurred_at=data.get("occurred_at"),
            note=data.get("note", ""),
        )
        if data["kind"] == Transaction.Kind.INCOME:
            tx = services.create_income(request.user, **common)
        else:
            tx = services.create_expense(
                request.user, category=data["category"], **common
            )
        return Response(TransactionSerializer(tx).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], permission_classes=[CanApproveFinance])
    def confirm(self, request, pk=None):
        """ФНС-01: подтверждение прихода финансистом."""
        tx = services.confirm_income(request.user, transaction_id=int(pk))
        return Response(TransactionSerializer(tx).data)

    @action(detail=True, methods=["post"])
    def void(self, request, pk=None):
        tx = services.void_transaction(request.user, transaction_id=int(pk))
        return Response(TransactionSerializer(tx).data)

    def destroy(self, request, pk=None):
        services.soft_delete_transaction(request.user, transaction_id=int(pk))
        return Response(status=status.HTTP_204_NO_CONTENT)


class ProfitView(APIView):
    """ФНС-04: прибыль по бизнесу/холдингу за период."""

    permission_classes = [FinanceSection]

    def get(self, request):
        date_from = request.query_params.get("date_from")
        date_to = request.query_params.get("date_to")
        businesses = rbac.accessible_businesses(request.user)
        business_id = request.query_params.get("business")
        if business_id:
            businesses = businesses.filter(id=business_id)
            if not businesses.exists():
                raise NotFoundError("Бизнес недоступен")
        data = selectors.profit_by_business(
            date_from=date_from or None,
            date_to=date_to or None,
            businesses=businesses,
        )
        # Деньги — строкой (ТЗ, раздел 10).
        for row in data["businesses"]:
            for k in ("income", "expense", "profit"):
                row[k] = str(row[k])
        data["total"] = {k: str(v) for k, v in data["total"].items()}
        return Response(data)
