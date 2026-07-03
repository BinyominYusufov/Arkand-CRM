from decimal import Decimal

from rest_framework import serializers

from .models import CashOperation, CashRegister


class CashRegisterSerializer(serializers.ModelSerializer):
    """Касса с остатком/оборотом (значения считает селектор во вьюхе)."""

    business_name = serializers.CharField(source="business.name", read_only=True)
    balance = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    month_turnover = serializers.DecimalField(
        max_digits=14, decimal_places=2, read_only=True
    )
    limit_utilization = serializers.FloatField(read_only=True)
    over_limit = serializers.BooleanField(read_only=True)

    class Meta:
        model = CashRegister
        fields = [
            "id",
            "name",
            "business",
            "business_name",
            "turnover_limit",
            "is_active",
            "balance",
            "month_turnover",
            "limit_utilization",
            "over_limit",
            "members",
        ]
        read_only_fields = ["balance", "month_turnover", "limit_utilization", "over_limit"]


class CashOperationSerializer(serializers.ModelSerializer):
    register_name = serializers.CharField(source="register.name", read_only=True)
    business_name = serializers.CharField(
        source="register.business.name", read_only=True
    )
    created_by_name = serializers.SerializerMethodField()

    class Meta:
        model = CashOperation
        fields = [
            "id",
            "register",
            "register_name",
            "business_name",
            "direction",
            "method",
            "amount",
            "note",
            "created_by",
            "created_by_name",
            "occurred_at",
            "created_at",
        ]
        read_only_fields = fields

    def get_created_by_name(self, obj) -> str:
        return str(obj.created_by) if obj.created_by else ""


class CashOperationCreateSerializer(serializers.Serializer):
    register = serializers.PrimaryKeyRelatedField(queryset=CashRegister.objects.all())
    direction = serializers.ChoiceField(choices=CashOperation.Direction.choices)
    method = serializers.ChoiceField(choices=CashOperation.Method.choices)
    amount = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=Decimal("0.01"))
    occurred_at = serializers.DateTimeField(required=False)
    note = serializers.CharField(required=False, allow_blank=True, default="")
