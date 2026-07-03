"""Передачи, долги, взаимозачёт, бартер (БАР-01…04, ХОЛ-30…33)."""
from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

from apps.core.models import Business, TimeStampedModel


class Transfer(TimeStampedModel):
    """Передача денег между бизнесами; при одобрении рождает долг (ХОЛ-30)."""

    class Status(models.TextChoices):
        PENDING = "pending", "Ожидает"
        APPROVED = "approved", "Одобрена"
        REJECTED = "rejected", "Отклонена"

    from_business = models.ForeignKey(
        Business,
        verbose_name="Откуда",
        on_delete=models.PROTECT,
        related_name="transfers_out",
    )
    to_business = models.ForeignKey(
        Business,
        verbose_name="Куда",
        on_delete=models.PROTECT,
        related_name="transfers_in",
    )
    amount = models.DecimalField(
        "Сумма",
        max_digits=14,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    status = models.CharField(
        "Статус", max_length=10, choices=Status.choices, default=Status.PENDING
    )
    # ХОЛ-32: сумма сверх порога — одобрение только владельцем.
    requires_owner_approval = models.BooleanField(
        "Требует одобрения владельцем", default=False
    )
    note = models.TextField("Примечание", blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="Создал",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_transfers",
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="Одобрил",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_transfers",
    )

    class Meta:
        verbose_name = "Передача"
        verbose_name_plural = "Передачи"
        ordering = ["-created_at", "-id"]
        constraints = [
            models.CheckConstraint(
                check=~models.Q(from_business=models.F("to_business")),
                name="settlements_transfer_not_self",
            ),
            models.CheckConstraint(
                check=models.Q(amount__gt=0), name="settlements_transfer_amount_positive"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.from_business} → {self.to_business}: {self.amount}"


class Debt(models.Model):
    """Долг между бизнесами. Автосоздаётся при одобрении передачи (БАР-01)."""

    class Status(models.TextChoices):
        OPEN = "open", "Открыт"
        CLOSED = "closed", "Закрыт"

    debtor = models.ForeignKey(
        Business,
        verbose_name="Должник",
        on_delete=models.PROTECT,
        related_name="debts_owed",
    )
    creditor = models.ForeignKey(
        Business,
        verbose_name="Кредитор",
        on_delete=models.PROTECT,
        related_name="debts_receivable",
    )
    amount = models.DecimalField(
        "Сумма",
        max_digits=14,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    status = models.CharField(
        "Статус", max_length=10, choices=Status.choices, default=Status.OPEN
    )
    source_transfer = models.ForeignKey(
        Transfer,
        verbose_name="Из передачи",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="debts",
    )
    created_at = models.DateTimeField("Создан", auto_now_add=True)
    closed_at = models.DateTimeField("Закрыт", null=True, blank=True)

    class Meta:
        verbose_name = "Долг"
        verbose_name_plural = "Долги"
        ordering = ["-created_at", "-id"]
        constraints = [
            models.CheckConstraint(
                check=~models.Q(debtor=models.F("creditor")),
                name="settlements_debt_not_self",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.debtor} должен {self.creditor}: {self.amount}"


class Barter(TimeStampedModel):
    """Бартер между бизнесами холдинга под контролем бухгалтера (БАР-04)."""

    class Status(models.TextChoices):
        ACTIVE = "active", "Активен"
        COMPLETED = "completed", "Завершён"
        CANCELLED = "cancelled", "Отменён"

    business_a = models.ForeignKey(
        Business,
        verbose_name="Сторона А",
        on_delete=models.PROTECT,
        related_name="barters_a",
    )
    business_b = models.ForeignKey(
        Business,
        verbose_name="Сторона Б",
        on_delete=models.PROTECT,
        related_name="barters_b",
    )
    description = models.TextField("Описание")
    value = models.DecimalField(
        "Оценка",
        max_digits=14,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    controlled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="Контролирует (бухгалтер)",
        on_delete=models.SET_NULL,
        null=True,
        related_name="controlled_barters",
    )
    status = models.CharField(
        "Статус", max_length=10, choices=Status.choices, default=Status.ACTIVE
    )

    class Meta:
        verbose_name = "Бартер"
        verbose_name_plural = "Бартеры"
        ordering = ["-created_at", "-id"]
        constraints = [
            models.CheckConstraint(
                check=~models.Q(business_a=models.F("business_b")),
                name="settlements_barter_not_self",
            ),
        ]

    def __str__(self) -> str:
        return f"Бартер {self.business_a} ↔ {self.business_b} на {self.value}"


class DebtSettlement(models.Model):
    """Погашение долга: взаимозачёт или возврат (БАР-03)."""

    class Method(models.TextChoices):
        OFFSET = "offset", "Взаимозачёт"
        RETURN = "return", "Возврат"

    debt = models.ForeignKey(
        Debt,
        verbose_name="Долг",
        on_delete=models.PROTECT,
        related_name="settlements",
    )
    method = models.CharField("Способ", max_length=10, choices=Method.choices)
    amount = models.DecimalField(
        "Сумма",
        max_digits=14,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    # ХОЛ-33: если долг закрыт бартером — ссылка на него.
    barter = models.ForeignKey(
        Barter,
        verbose_name="Бартер",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="debt_settlements",
    )
    note = models.TextField("Примечание", blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="Создал",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="debt_settlements",
    )
    created_at = models.DateTimeField("Создано", auto_now_add=True)

    class Meta:
        verbose_name = "Погашение долга"
        verbose_name_plural = "Погашения долгов"
        ordering = ["-created_at", "-id"]

    def __str__(self) -> str:
        return f"{self.get_method_display()} {self.amount} по долгу #{self.debt_id}"
