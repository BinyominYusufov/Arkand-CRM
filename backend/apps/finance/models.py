"""Модели финансов: категории расходов и операции (ФНС-01…04).

Только структура данных и инварианты записи — бизнес-логика в services.py.
"""
from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from apps.core.models import Business, SoftDeleteModel, TimeStampedModel


class ExpenseCategory(models.Model):
    """Справочник категорий расходов (ФНС-02)."""

    name = models.CharField("Название", max_length=255, unique=True)
    code = models.SlugField("Код", max_length=64, unique=True)

    class Meta:
        verbose_name = "Категория расходов"
        verbose_name_plural = "Категории расходов"
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class TransactionQuerySet(models.QuerySet):
    def alive(self):
        return self.filter(is_deleted=False)

    def confirmed(self):
        return self.alive().filter(status=Transaction.Status.CONFIRMED)


class Transaction(TimeStampedModel, SoftDeleteModel):
    """Приход или расход бизнеса (ФНС-01…03).

    Деньги — только Decimal(14,2). Soft-delete вместо физического удаления.
    """

    class Kind(models.TextChoices):
        INCOME = "income", "Приход"
        EXPENSE = "expense", "Расход"

    class Method(models.TextChoices):
        CASH = "cash", "Наличные"
        TRANSFER = "transfer", "Перевод"

    class Status(models.TextChoices):
        PENDING = "pending", "Ожидает подтверждения"
        CONFIRMED = "confirmed", "Подтверждено"
        VOID = "void", "Аннулировано"

    business = models.ForeignKey(
        Business,
        verbose_name="Бизнес",
        on_delete=models.PROTECT,
        related_name="transactions",
    )
    kind = models.CharField("Тип", max_length=10, choices=Kind.choices)
    category = models.ForeignKey(
        ExpenseCategory,
        verbose_name="Категория",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="transactions",
        help_text="Обязательна для расхода, пуста для прихода",
    )
    amount = models.DecimalField(
        "Сумма",
        max_digits=14,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    method = models.CharField("Способ оплаты", max_length=10, choices=Method.choices)
    status = models.CharField(
        "Статус", max_length=10, choices=Status.choices, default=Status.PENDING
    )
    confirmed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="Подтвердил",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="confirmed_transactions",
    )
    occurred_at = models.DateTimeField("Дата операции", default=timezone.now)
    note = models.TextField("Примечание", blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="Создал",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_transactions",
    )

    objects = TransactionQuerySet.as_manager()

    class Meta:
        verbose_name = "Операция"
        verbose_name_plural = "Операции"
        ordering = ["-occurred_at", "-id"]
        indexes = [
            models.Index(fields=["business", "kind", "status"]),
            models.Index(fields=["occurred_at"]),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(amount__gt=0), name="finance_tx_amount_positive"
            ),
            # Расход обязан иметь категорию (ФНС-02).
            models.CheckConstraint(
                check=~models.Q(kind="expense") | models.Q(category__isnull=False),
                name="finance_expense_requires_category",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.get_kind_display()} {self.amount} · {self.business}"
