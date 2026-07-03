"""Часть 0 — базовый слой холдинга: Holding, Business, User, роли, доступ.

# TODO: свериться с реальной Частью 0, когда появится ТЗ.
Минимум, на который опирается финмодуль, — ничего лишнего.
"""
from django.contrib.auth.models import AbstractUser, UserManager
from django.db import models

from . import roles as role_codes


# --- Базовые абстракции: наследуют все модули ---
class TimeStampedModel(models.Model):
    created_at = models.DateTimeField("Создано", auto_now_add=True)
    updated_at = models.DateTimeField("Обновлено", auto_now=True)

    class Meta:
        abstract = True


class SoftDeleteModel(models.Model):
    """Финансовые записи физически не удаляются (ТЗ, раздел 11)."""

    is_deleted = models.BooleanField("Удалено", default=False)

    class Meta:
        abstract = True


class Holding(models.Model):
    """Единая сущность холдинга. Один экземпляр (создаётся в seed)."""

    name = models.CharField("Название", max_length=255, default="ARKAND")
    requisites = models.JSONField("Реквизиты", default=dict, blank=True)

    class Meta:
        verbose_name = "Холдинг"
        verbose_name_plural = "Холдинг"

    def __str__(self) -> str:
        return self.name


class Business(models.Model):
    """Бизнес холдинга (завод / застройщик / проектная / торговый / прочее)."""

    class Kind(models.TextChoices):
        FACTORY = "factory", "Завод"
        DEVELOPER = "developer", "Застройщик"
        DESIGN = "design", "Проектная организация"
        TRADING = "trading", "Торговый"
        OTHER = "other", "Прочее"

    holding = models.ForeignKey(
        Holding,
        verbose_name="Холдинг",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="businesses",
    )
    name = models.CharField("Название", max_length=255, unique=True)
    code = models.SlugField("Код", max_length=64, unique=True)
    kind = models.CharField("Тип", max_length=20, choices=Kind.choices)
    is_active = models.BooleanField("Активен", default=True)

    class Meta:
        verbose_name = "Бизнес"
        verbose_name_plural = "Бизнесы"
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class Role(models.Model):
    """Роль холдинга — data-driven: добавляется строкой в БД, без кода."""

    code = models.SlugField("Код", max_length=64, unique=True)
    name = models.CharField("Название", max_length=255)
    is_active = models.BooleanField("Активна", default=True)

    class Meta:
        verbose_name = "Роль"
        verbose_name_plural = "Роли"
        ordering = ["code"]

    def __str__(self) -> str:
        return self.name


class RolePermission(models.Model):
    """Право роли (код из apps.core.rbac). Наполняется из seed/конфига."""

    role = models.ForeignKey(
        Role, verbose_name="Роль", on_delete=models.CASCADE, related_name="permissions"
    )
    perm = models.CharField("Право", max_length=64)

    class Meta:
        verbose_name = "Право роли"
        verbose_name_plural = "Права ролей"
        constraints = [
            models.UniqueConstraint(fields=["role", "perm"], name="core_role_perm_unique")
        ]

    def __str__(self) -> str:
        return f"{self.role.code}: {self.perm}"


class ArkandUserManager(UserManager):
    def get_by_natural_key(self, username):
        # Вход по email без учёта регистра.
        return self.get(**{f"{self.model.USERNAME_FIELD}__iexact": username})


class User(AbstractUser):
    """Пользователь холдинга (Часть 0)."""

    email = models.EmailField("Email", unique=True)
    phone = models.CharField("Телефон", max_length=32, blank=True)
    full_name = models.CharField("ФИО", max_length=255, blank=True)
    # Код роли из справочника Role; стабильные коды — в apps.core.roles.
    role = models.CharField("Роль", max_length=32, default=role_codes.CASHIER)
    business = models.ForeignKey(
        Business,
        verbose_name="Бизнес",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="users",
        help_text="Пусто для финотдела и владельцев",
    )

    objects = ArkandUserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    class Meta:
        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"

    def __str__(self) -> str:
        return self.full_name or self.email

    # --- удобные проверки ролей (сервисы/селекторы) ---
    @property
    def is_finance(self) -> bool:
        """Финотдел: главбух и бухгалтеры."""
        return self.role in role_codes.FINANCE_ROLES

    @property
    def is_chief_accountant(self) -> bool:
        return self.role == role_codes.CHIEF_ACCOUNTANT

    @property
    def is_owner_role(self) -> bool:
        return self.role == role_codes.OWNER

    @property
    def is_cashier(self) -> bool:
        return self.role == role_codes.CASHIER


class BusinessAccess(models.Model):
    """Доступ «пользователь ↔ бизнес»: кто какие бизнесы видит (Часть 0).

    Финансовая изоляция (КАС-04) и права финмодуля опираются на это:
    финотдел/владельцы видят все бизнесы (business.view_all),
    остальные — только бизнесы из этой таблицы + собственную привязку.
    """

    user = models.ForeignKey(
        User, verbose_name="Пользователь", on_delete=models.CASCADE,
        related_name="business_access",
    )
    business = models.ForeignKey(
        Business, verbose_name="Бизнес", on_delete=models.CASCADE,
        related_name="user_access",
    )

    class Meta:
        verbose_name = "Доступ к бизнесу"
        verbose_name_plural = "Доступы к бизнесам"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "business"], name="core_business_access_unique"
            )
        ]

    def __str__(self) -> str:
        return f"{self.user} → {self.business}"
