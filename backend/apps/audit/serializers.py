from rest_framework import serializers

from .models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    actor_name = serializers.SerializerMethodField()

    class Meta:
        model = AuditLog
        fields = [
            "id",
            "actor",
            "actor_name",
            "action",
            "entity_type",
            "entity_id",
            "before",
            "after",
            "created_at",
        ]

    def get_actor_name(self, obj) -> str:
        return str(obj.actor) if obj.actor else ""
