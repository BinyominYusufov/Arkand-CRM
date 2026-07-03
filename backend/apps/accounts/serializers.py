from rest_framework import serializers

from apps.core import rbac
from apps.core.models import User
from apps.core.serializers import BusinessSerializer


class MeSerializer(serializers.ModelSerializer):
    """Профиль: роль, права и доступные бизнесы (Часть 0) — опора фронтенда."""

    business = BusinessSerializer(read_only=True)
    businesses = serializers.SerializerMethodField()
    permissions = serializers.SerializerMethodField()
    cash_register_ids = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "username",
            "full_name",
            "phone",
            "role",
            "business",
            "businesses",
            "permissions",
            "cash_register_ids",
        ]

    def get_businesses(self, obj) -> list[dict]:
        return BusinessSerializer(rbac.accessible_businesses(obj), many=True).data

    def get_permissions(self, obj) -> list[str]:
        return rbac.user_permissions(obj)

    def get_cash_register_ids(self, obj) -> list[int]:
        return list(obj.cash_registers.values_list("id", flat=True))
