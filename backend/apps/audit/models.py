from django.conf import settings
from django.db import models


class AuditLog(models.Model):
    """Журнал действий: каждое изменение денег/статусов (ТЗ, раздел 11)."""

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="Кто",
        on_delete=models.SET_NULL,
        null=True,
        related_name="audit_logs",
    )
    action = models.CharField("Действие", max_length=64)
    entity_type = models.CharField("Тип объекта", max_length=64)
    entity_id = models.CharField("ID объекта", max_length=64)
    before = models.JSONField("До", null=True, blank=True)
    after = models.JSONField("После", null=True, blank=True)
    created_at = models.DateTimeField("Когда", auto_now_add=True)

    class Meta:
        verbose_name = "Запись аудита"
        verbose_name_plural = "Журнал аудита"
        ordering = ["-created_at", "-id"]
        indexes = [models.Index(fields=["entity_type", "entity_id"])]

    def __str__(self) -> str:
        return f"{self.action} {self.entity_type}#{self.entity_id}"

    @classmethod
    def record(cls, actor, action: str, entity, *, before=None, after=None) -> "AuditLog":
        """Единая точка записи аудита из сервисов."""
        return cls.objects.create(
            actor=actor if getattr(actor, "pk", None) else None,
            action=action,
            entity_type=entity.__class__.__name__,
            entity_id=str(entity.pk),
            before=before,
            after=after,
        )
