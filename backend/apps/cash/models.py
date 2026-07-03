"""Кассы и операции (КАС-01…04). Логика — в services/selectors."""
from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from apps.core.models import Business, SoftDeleteModel, TimeStampedModel


class CashRegister(TimeStampedModel):
    """Касса бизнеса (КАС-01). На заводах роль кассы — оператор/продажник:
    просто пользователь, привязанный к кассе через members."""

    name = models.CharField("Название", max_length=255)
    business = models.ForeignKey(
        Business,
        verbose_name="Бизнес",
        on_delete=models.PROTECT,
        related_name="cash_registers",
    )
    turnover_limit = models.DecimalField(
        "Лимит оборота (месяц)",
        max_digits=14,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    members = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        verbose_name="Ответственные",
        related_name="cash_registers",
        blank=True,
    )
    is_active = models.BooleanField("Активна", default=True)

    class Meta:
        verbose_name = "Касса"
        verbose_name_plural = "Кассы"
        ordering = ["business__name", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["business", "name"], name="cash_register_name_unique_per_business"
            )
        ]

    def __str__(self) -> str:
        return f"{self.name} · {self.business}"


class CashOperationQuerySet(models.QuerySet):
    def alive(self):
        return self.filter(is_deleted=False)


class CashOperation(TimeStampedModel, SoftDeleteModel):
    """Операция кассы (КАС-02): остаток кассы = сумма операций."""

    class Direction(models.TextChoices):
        IN = "in", "Приход"
        OUT = "out", "Расход"

    class Method(models.TextChoices):
        CASH = "cash", "Наличные"
        TRANSFER = "transfer", "Перевод"

    register = models.ForeignKey(
        CashRegister,
        verbose_name="Касса",
        on_delete=models.PROTECT,
        related_name="operations",
    )
    direction = models.CharField("Направление", max_length=3, choices=Direction.choices)
    method = models.CharField("Способ оплаты", max_length=10, choices=Method.choices)
    amount = models.DecimalField(
        "Сумма",
        max_digits=14,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    note = models.TextField("Примечание", blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="Создал",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cash_operations",
    )
    occurred_at = models.DateTimeField("Дата операции", default=timezone.now)

    objects = CashOperationQuerySet.as_manager()

    class Meta:
        verbose_name = "Операция кассы"
        verbose_name_plural = "Операции касс"
        ordering = ["-occurred_at", "-id"]
        indexes = [models.Index(fields=["register", "occurred_at"])]
        constraints = [
            models.CheckConstraint(
                check=models.Q(amount__gt=0), name="cash_op_amount_positive"
            )
        ]

    def __str__(self) -> str:
        return f"{self.get_direction_display()} {self.amount} · {self.register}"
