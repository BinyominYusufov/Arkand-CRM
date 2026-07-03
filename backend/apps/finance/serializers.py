from decimal import Decimal

from rest_framework import serializers

from apps.core.models import Business

from .models import ExpenseCategory, Transaction


class ExpenseCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ExpenseCategory
        fields = ["id", "name", "code"]


class TransactionSerializer(serializers.ModelSerializer):
    """Чтение операции. Деньги (Decimal) сериализуются строкой."""

    business_name = serializers.CharField(source="business.name", read_only=True)
    category_name = serializers.CharField(
        source="category.name", read_only=True, default=None
    )
    confirmed_by_name = serializers.SerializerMethodField()
    created_by_name = serializers.SerializerMethodField()

    class Meta:
        model = Transaction
        fields = [
            "id",
            "business",
            "business_name",
            "kind",
            "category",
            "category_name",
            "amount",
            "method",
            "status",
            "confirmed_by",
            "confirmed_by_name",
            "created_by",
            "created_by_name",
            "occurred_at",
            "note",
            "created_at",
        ]
        read_only_fields = fields

    def get_confirmed_by_name(self, obj) -> str:
        return str(obj.confirmed_by) if obj.confirmed_by else ""

    def get_created_by_name(self, obj) -> str:
        return str(obj.created_by) if obj.created_by else ""


class TransactionCreateSerializer(serializers.Serializer):
    """Вход на создание операции; сама запись — в services."""

    business = serializers.PrimaryKeyRelatedField(
        queryset=Business.objects.filter(is_active=True)
    )
    kind = serializers.ChoiceField(choices=Transaction.Kind.choices)
    category = serializers.PrimaryKeyRelatedField(
        queryset=ExpenseCategory.objects.all(), required=False, allow_null=True
    )
    amount = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=Decimal("0.01"))
    method = serializers.ChoiceField(choices=Transaction.Method.choices)
    occurred_at = serializers.DateTimeField(required=False)
    note = serializers.CharField(required=False, allow_blank=True, default="")

    def validate(self, attrs):
        if attrs["kind"] == Transaction.Kind.EXPENSE and not attrs.get("category"):
            raise serializers.ValidationError(
                {"category": "Для расхода обязательна категория"}
            )
        if attrs["kind"] == Transaction.Kind.INCOME and attrs.get("category"):
            raise serializers.ValidationError(
                {"category": "Для прихода категория не указывается"}
            )
        return attrs
