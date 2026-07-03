from rest_framework import serializers

from .models import Business, Role, User


class BusinessSerializer(serializers.ModelSerializer):
    kind_display = serializers.CharField(source="get_kind_display", read_only=True)

    class Meta:
        model = Business
        fields = ["id", "name", "code", "kind", "kind_display", "is_active"]


class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = ["id", "code", "name", "is_active"]


class UserListSerializer(serializers.ModelSerializer):
    business_name = serializers.CharField(source="business.name", read_only=True, default="")

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "full_name",
            "phone",
            "role",
            "business",
            "business_name",
            "is_active",
        ]
