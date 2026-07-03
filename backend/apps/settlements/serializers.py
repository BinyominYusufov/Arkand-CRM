from decimal import Decimal

from rest_framework import serializers

from apps.core.models import Business, User

from . import services
from .models import Barter, Debt, DebtSettlement, Transfer


class TransferSerializer(serializers.ModelSerializer):
    from_business_name = serializers.CharField(source="from_business.name", read_only=True)
    to_business_name = serializers.CharField(source="to_business.name", read_only=True)
    created_by_name = serializers.SerializerMethodField()
    approved_by_name = serializers.SerializerMethodField()

    class Meta:
        model = Transfer
        fields = [
            "id",
            "from_business",
            "from_business_name",
            "to_business",
            "to_business_name",
            "amount",
            "status",
            "requires_owner_approval",
            "note",
            "created_by",
            "created_by_name",
            "approved_by",
            "approved_by_name",
            "created_at",
        ]
        read_only_fields = fields

    def get_created_by_name(self, obj) -> str:
        return str(obj.created_by) if obj.created_by else ""

    def get_approved_by_name(self, obj) -> str:
        return str(obj.approved_by) if obj.approved_by else ""


class TransferCreateSerializer(serializers.Serializer):
    from_business = serializers.PrimaryKeyRelatedField(
        queryset=Business.objects.filter(is_active=True)
    )
    to_business = serializers.PrimaryKeyRelatedField(
        queryset=Business.objects.filter(is_active=True)
    )
    amount = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=Decimal("0.01"))
    note = serializers.CharField(required=False, allow_blank=True, default="")

    def validate(self, attrs):
        if attrs["from_business"] == attrs["to_business"]:
            raise serializers.ValidationError(
                {"to_business": "Нельзя передавать самому себе"}
            )
        return attrs


class DebtSettlementSerializer(serializers.ModelSerializer):
    class Meta:
        model = DebtSettlement
        fields = ["id", "debt", "method", "amount", "barter", "note", "created_by", "created_at"]
        read_only_fields = fields


class DebtSerializer(serializers.ModelSerializer):
    debtor_name = serializers.CharField(source="debtor.name", read_only=True)
    creditor_name = serializers.CharField(source="creditor.name", read_only=True)
    remaining = serializers.SerializerMethodField()
    is_overdue = serializers.SerializerMethodField()
    settlements = DebtSettlementSerializer(many=True, read_only=True)

    class Meta:
        model = Debt
        fields = [
            "id",
            "debtor",
            "debtor_name",
            "creditor",
            "creditor_name",
            "amount",
            "remaining",
            "status",
            "is_overdue",
            "source_transfer",
            "settlements",
            "created_at",
            "closed_at",
        ]
        read_only_fields = fields

    def get_remaining(self, obj) -> str:
        return str(services.debt_remaining(obj))

    def get_is_overdue(self, obj) -> bool:
        from . import selectors

        return selectors.is_debt_overdue(obj)


class SettleDebtSerializer(serializers.Serializer):
    method = serializers.ChoiceField(choices=DebtSettlement.Method.choices)
    amount = serializers.DecimalField(
        max_digits=14, decimal_places=2, min_value=Decimal("0.01"), required=False, allow_null=True
    )
    note = serializers.CharField(required=False, allow_blank=True, default="")


class BarterSerializer(serializers.ModelSerializer):
    business_a_name = serializers.CharField(source="business_a.name", read_only=True)
    business_b_name = serializers.CharField(source="business_b.name", read_only=True)
    controlled_by_name = serializers.SerializerMethodField()

    class Meta:
        model = Barter
        fields = [
            "id",
            "business_a",
            "business_a_name",
            "business_b",
            "business_b_name",
            "description",
            "value",
            "controlled_by",
            "controlled_by_name",
            "status",
            "created_at",
        ]
        read_only_fields = fields

    def get_controlled_by_name(self, obj) -> str:
        return str(obj.controlled_by) if obj.controlled_by else ""


class BarterCreateSerializer(serializers.Serializer):
    business_a = serializers.PrimaryKeyRelatedField(
        queryset=Business.objects.filter(is_active=True)
    )
    business_b = serializers.PrimaryKeyRelatedField(
        queryset=Business.objects.filter(is_active=True)
    )
    description = serializers.CharField()
    value = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=Decimal("0.01"))
    controlled_by = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(is_active=True)
    )

    def validate(self, attrs):
        if attrs["business_a"] == attrs["business_b"]:
            raise serializers.ValidationError(
                {"business_b": "Бартер требует два разных бизнеса"}
            )
        return attrs


class NetDebtsSerializer(serializers.Serializer):
    business_a = serializers.PrimaryKeyRelatedField(
        queryset=Business.objects.filter(is_active=True)
    )
    business_b = serializers.PrimaryKeyRelatedField(
        queryset=Business.objects.filter(is_active=True)
    )


class BarterCloseDebtSerializer(serializers.Serializer):
    debt = serializers.PrimaryKeyRelatedField(queryset=Debt.objects.all())
