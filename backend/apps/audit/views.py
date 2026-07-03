from rest_framework import viewsets

from apps.core.permissions import CanViewAudit

from .models import AuditLog
from .serializers import AuditLogSerializer


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    """Журнал аудита — только чтение, только финотдел и владельцы."""

    queryset = AuditLog.objects.select_related("actor").all()
    serializer_class = AuditLogSerializer
    permission_classes = [CanViewAudit]
    filterset_fields = ["action", "entity_type", "entity_id", "actor"]
    ordering = ["-created_at"]
