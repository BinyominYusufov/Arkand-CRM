"""Тонкие вьюхи взаиморасчётов: сервисы делают всю работу."""
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import CanApproveSettlements, SettlementsSection

from . import selectors, services
from .models import Barter, Debt, Transfer
from .serializers import (
    BarterCloseDebtSerializer,
    BarterCreateSerializer,
    BarterSerializer,
    DebtSerializer,
    NetDebtsSerializer,
    SettleDebtSerializer,
    TransferCreateSerializer,
    TransferSerializer,
)


class TransferViewSet(
    mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet
):
    serializer_class = TransferSerializer
    permission_classes = [SettlementsSection]
    filterset_fields = ["status", "from_business", "to_business"]
    ordering_fields = ["created_at", "amount"]

    def get_queryset(self):
        return Transfer.objects.select_related(
            "from_business", "to_business", "created_by", "approved_by"
        )

    def create(self, request):
        ser = TransferCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        tr = services.create_transfer(
            request.user,
            from_business=ser.validated_data["from_business"],
            to_business=ser.validated_data["to_business"],
            amount=ser.validated_data["amount"],
            note=ser.validated_data.get("note", ""),
        )
        return Response(TransferSerializer(tr).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], permission_classes=[CanApproveSettlements])
    def approve(self, request, pk=None):
        """БАР-01/ХОЛ-30: одобрение → авто-долг; ХОЛ-32: порог владельца."""
        services.approve_transfer(transfer_id=int(pk), actor=request.user)
        tr = Transfer.objects.get(pk=pk)
        return Response(TransferSerializer(tr).data)

    @action(detail=True, methods=["post"], permission_classes=[CanApproveSettlements])
    def reject(self, request, pk=None):
        tr = services.reject_transfer(request.user, transfer_id=int(pk))
        return Response(TransferSerializer(tr).data)


class DebtViewSet(
    mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet
):
    serializer_class = DebtSerializer
    permission_classes = [SettlementsSection]
    filterset_fields = ["status", "debtor", "creditor"]
    ordering_fields = ["created_at", "amount"]

    def get_queryset(self):
        return Debt.objects.select_related(
            "debtor", "creditor", "source_transfer"
        ).prefetch_related("settlements")

    @action(detail=True, methods=["post"])
    def settle(self, request, pk=None):
        """БАР-03: закрытие долга — взаимозачёт или возврат."""
        ser = SettleDebtSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        services.settle_debt(
            request.user,
            debt_id=int(pk),
            method=ser.validated_data["method"],
            amount=ser.validated_data.get("amount"),
            note=ser.validated_data.get("note", ""),
        )
        return Response(DebtSerializer(Debt.objects.get(pk=pk)).data)

    @action(detail=False, methods=["get"])
    def registry(self, request):
        """БАР-02: реестр «кто кому должен» (деньги — строкой)."""
        data = selectors.debts_registry()
        for row in data["debts"]:
            row["amount"] = str(row["amount"])
            row["remaining"] = str(row["remaining"])
        for pair in data["pairs"]:
            pair["total_remaining"] = str(pair["total_remaining"])
        data["total_open"] = str(data["total_open"])
        return Response(data)


class NetDebtsView(APIView):
    """ХОЛ-31: двусторонний взаимозачёт встречных долгов."""

    permission_classes = [SettlementsSection]

    def post(self, request):
        ser = NetDebtsSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        result = services.net_debts(
            request.user,
            business_a=ser.validated_data["business_a"],
            business_b=ser.validated_data["business_b"],
        )
        return Response({k: str(v) for k, v in result.items()})


class BarterViewSet(
    mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet
):
    serializer_class = BarterSerializer
    permission_classes = [SettlementsSection]
    filterset_fields = ["status", "business_a", "business_b"]

    def get_queryset(self):
        return Barter.objects.select_related("business_a", "business_b", "controlled_by")

    def create(self, request):
        ser = BarterCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        barter = services.create_barter(
            request.user,
            business_a=ser.validated_data["business_a"],
            business_b=ser.validated_data["business_b"],
            description=ser.validated_data["description"],
            value=ser.validated_data["value"],
            controlled_by=ser.validated_data["controlled_by"],
        )
        return Response(BarterSerializer(barter).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        barter = services.complete_barter(request.user, barter_id=int(pk))
        return Response(BarterSerializer(barter).data)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        barter = services.cancel_barter(request.user, barter_id=int(pk))
        return Response(BarterSerializer(barter).data)

    @action(detail=True, methods=["post"], url_path="close-debt")
    def close_debt(self, request, pk=None):
        """ХОЛ-33: закрыть встречный долг бартером."""
        ser = BarterCloseDebtSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        settlement = services.close_debt_with_barter(
            request.user, barter_id=int(pk), debt_id=ser.validated_data["debt"].pk
        )
        return Response(
            DebtSerializer(Debt.objects.get(pk=settlement.debt_id)).data
        )
