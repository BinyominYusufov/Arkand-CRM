"""Зарплата (ЗРП-01…05): сотрудники, гибкие схемы, расчётные периоды."""
from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from apps.core.models import Business, TimeStampedModel


class Employee(TimeStampedModel):
    """Сотрудник (ЗРП-02): объектный или административный персонал."""

    class SalaryType(models.TextChoices):
        OBJECTIVE = "objective", "Объектный"
        ADMINISTRATIVE = "administrative", "Административный"

    full_name = models.CharField("ФИО", max_length=255)
    business = models.ForeignKey(
        Business,
        verbose_name="Бизнес",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="employees",
        help_text="Пусто для административного персонала головного офиса",
    )
    position = models.CharField("Должность", max_length=255, blank=True)
    salary_type = models.CharField(
        "Тип оплаты", max_length=20, choices=SalaryType.choices
    )
    is_salesperson = models.BooleanField("Продажник", default=False)
    is_active = models.BooleanField("Активен", default=True)

    class Meta:
        verbose_name = "Сотрудник"
        verbose_name_plural = "Сотрудники"
        ordering = ["full_name"]

    def __str__(self) -> str:
        return self.full_name


class SalaryScheme(TimeStampedModel):
    """Гибкая схема зарплаты (ЗРП-03…05): тип + config (JSON).

    Примеры config (цифры — примеры, не константы):
      fixed:            {"base": 3000}
      percent_of_sales: {"base": 3000, "percent": 10}
      per_unit_tiered:  {"base": 3000, "unit": "квартира", "tier_mode": "flat",
                         "tiers": [{"upto": 10, "rate": 500},
                                   {"upto": null, "rate": 1000}]}
    """

    class SchemeType(models.TextChoices):
        FIXED = "fixed", "Оклад"
        PERCENT_OF_SALES = "percent_of_sales", "Процент от продаж"
        PER_UNIT_TIERED = "per_unit_tiered", "За единицу со ступенями"

    employee = models.ForeignKey(
        Employee,
        verbose_name="Сотрудник",
        on_delete=models.PROTECT,
        related_name="schemes",
    )
    scheme_type = models.CharField(
        "Тип схемы", max_length=32, choices=SchemeType.choices
    )
    config = models.JSONField("Конфигурация", default=dict)
    is_active = models.BooleanField("Активна", default=True)

    class Meta:
        verbose_name = "Схема зарплаты"
        verbose_name_plural = "Схемы зарплаты"
        ordering = ["employee__full_name"]

    def __str__(self) -> str:
        return f"{self.employee} · {self.get_scheme_type_display()}"


class PayrollRun(TimeStampedModel):
    """Расчёт зарплаты за месяц (ЗРП-01: выплата из головного офиса)."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Черновик"
        FINALIZED = "finalized", "Утверждён"

    year = models.PositiveSmallIntegerField(
        "Год", validators=[MinValueValidator(2020), MaxValueValidator(2100)]
    )
    month = models.PositiveSmallIntegerField(
        "Месяц", validators=[MinValueValidator(1), MaxValueValidator(12)]
    )
    status = models.CharField(
        "Статус", max_length=12, choices=Status.choices, default=Status.DRAFT
    )
    paid_from_hq = models.BooleanField("Выплата из головного офиса", default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="Создал",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="payroll_runs",
    )
    finalized_at = models.DateTimeField("Утверждён", null=True, blank=True)

    class Meta:
        verbose_name = "Расчёт зарплаты"
        verbose_name_plural = "Расчёты зарплаты"
        ordering = ["-year", "-month"]
        constraints = [
            models.UniqueConstraint(fields=["year", "month"], name="payroll_run_period_unique")
        ]

    def __str__(self) -> str:
        return f"Зарплата {self.month:02d}.{self.year} ({self.get_status_display()})"


class PayrollItem(models.Model):
    """Строка расчёта: base + bonus = total; breakdown — как посчитано."""

    run = models.ForeignKey(
        PayrollRun,
        verbose_name="Расчёт",
        on_delete=models.PROTECT,
        related_name="items",
    )
    employee = models.ForeignKey(
        Employee,
        verbose_name="Сотрудник",
        on_delete=models.PROTECT,
        related_name="payroll_items",
    )
    base = models.DecimalField("Оклад", max_digits=14, decimal_places=2)
    bonus = models.DecimalField("Бонус", max_digits=14, decimal_places=2)
    total = models.DecimalField("Итого", max_digits=14, decimal_places=2)
    breakdown = models.JSONField("Разбивка", default=dict)

    class Meta:
        verbose_name = "Строка расчёта"
        verbose_name_plural = "Строки расчёта"
        ordering = ["employee__full_name"]
        constraints = [
            models.UniqueConstraint(
                fields=["run", "employee"], name="payroll_item_unique_per_run"
            )
        ]

    def __str__(self) -> str:
        return f"{self.employee}: {self.total}"
