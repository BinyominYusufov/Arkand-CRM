"""Data-driven RBAC (Часть 0).

Права — строковые коды; сопоставление «роль → права» живёт в БД
(RolePermission) и наполняется из DEFAULT_ROLE_PERMISSIONS при seed.
Добавить роль = добавить строки в БД, код менять не нужно.

Если для роли в БД нет ни одной записи (юнит-тесты без seed) —
используется DEFAULT_ROLE_PERMISSIONS как fallback, чтобы поведение
было единым и предсказуемым.

# TODO: заменить на реальные правила, когда появится ТЗ Части 0.
"""
from __future__ import annotations

from . import roles as R

# --- Реестр кодов прав финмодуля ---
PERM_BUSINESS_VIEW_ALL = "business.view_all"
PERM_BUSINESS_MANAGE = "business.manage"
PERM_USERS_VIEW = "users.view"

PERM_FINANCE_VIEW = "finance.view"
PERM_FINANCE_MANAGE = "finance.manage"
PERM_FINANCE_APPROVE = "finance.approve"

PERM_CASH_VIEW = "cash.view"
PERM_CASH_VIEW_ALL = "cash.view_all"
PERM_CASH_OPERATE = "cash.operate"
PERM_CASH_MANAGE = "cash.manage"

PERM_SETTLEMENTS_VIEW = "settlements.view"
PERM_SETTLEMENTS_MANAGE = "settlements.manage"
PERM_SETTLEMENTS_APPROVE = "settlements.approve"

PERM_PAYROLL_VIEW = "payroll.view"
PERM_PAYROLL_MANAGE = "payroll.manage"

PERM_REPORTS_VIEW = "reports.view"
PERM_AUDIT_VIEW = "audit.view"
PERM_OVERLAY_VIEW = "overlay.view"  # Часть 7: только владельцы

# --- Дефолтная ролевая матрица (предварительные допущения) ---
# TODO: заменить на реальные правила Части 0 / Части 7.
_FINANCE_DEPT = (
    PERM_BUSINESS_VIEW_ALL,
    PERM_USERS_VIEW,
    PERM_FINANCE_VIEW,
    PERM_FINANCE_MANAGE,
    PERM_FINANCE_APPROVE,
    PERM_CASH_VIEW,
    PERM_CASH_VIEW_ALL,
    PERM_CASH_OPERATE,
    PERM_CASH_MANAGE,
    PERM_SETTLEMENTS_VIEW,
    PERM_SETTLEMENTS_MANAGE,
    PERM_SETTLEMENTS_APPROVE,
    PERM_PAYROLL_VIEW,
    PERM_PAYROLL_MANAGE,
    PERM_REPORTS_VIEW,
    PERM_AUDIT_VIEW,
)

DEFAULT_ROLE_PERMISSIONS: dict[str, tuple[str, ...]] = {
    R.CHIEF_ACCOUNTANT: _FINANCE_DEPT,
    R.ACCOUNTANT: _FINANCE_DEPT,
    # Владельцы: контроль финансов — чтение + согласования (approve), overlay.
    R.OWNER: (
        PERM_BUSINESS_VIEW_ALL,
        PERM_BUSINESS_MANAGE,
        PERM_USERS_VIEW,
        PERM_FINANCE_VIEW,
        PERM_FINANCE_APPROVE,
        PERM_CASH_VIEW,
        PERM_CASH_VIEW_ALL,
        PERM_SETTLEMENTS_VIEW,
        PERM_SETTLEMENTS_APPROVE,
        PERM_PAYROLL_VIEW,
        PERM_REPORTS_VIEW,
        PERM_AUDIT_VIEW,
        PERM_OVERLAY_VIEW,
    ),
    # Кассир: только свои кассы, в пределах лимита (КАС-04).
    R.CASHIER: (PERM_CASH_VIEW, PERM_CASH_OPERATE),
    # Директор бизнеса: сводные отчёты. TODO: уточнить по Части 0.
    R.DIRECTOR: (PERM_BUSINESS_VIEW_ALL, PERM_REPORTS_VIEW),
    # Менеджер/оператор: доступ к своему бизнесу, без финансов.
    R.MANAGER: (),
    R.OPERATOR: (),
}


def role_permissions(role_code: str) -> frozenset[str]:
    """Права роли: из БД (RolePermission), fallback — дефолтная матрица."""
    from .models import RolePermission

    db_perms = RolePermission.objects.filter(role__code=role_code).values_list(
        "perm", flat=True
    )
    perms = frozenset(db_perms)
    if perms:
        return perms
    return frozenset(DEFAULT_ROLE_PERMISSIONS.get(role_code, ()))


def user_has_perm(user, perm: str) -> bool:
    if not (user and getattr(user, "is_authenticated", False) and user.is_active):
        return False
    if user.is_superuser:
        return True
    cache = getattr(user, "_arkand_perm_cache", None)
    if cache is None:
        cache = role_permissions(user.role)
        user._arkand_perm_cache = cache
    return perm in cache


def user_permissions(user) -> list[str]:
    """Полный список прав пользователя (для /me и фронтенда)."""
    if not (user and getattr(user, "is_authenticated", False)):
        return []
    if user.is_superuser:
        return sorted(
            {p for perms in DEFAULT_ROLE_PERMISSIONS.values() for p in perms}
        )
    return sorted(role_permissions(user.role))


def accessible_businesses(user):
    """Какие бизнесы видит пользователь (Часть 0, BusinessAccess).

    Финотдел/владельцы (business.view_all) — все активные бизнесы;
    остальные — по BusinessAccess плюс собственная привязка.
    """
    from .models import Business

    if not (user and getattr(user, "is_authenticated", False)):
        return Business.objects.none()
    if user_has_perm(user, PERM_BUSINESS_VIEW_ALL):
        return Business.objects.filter(is_active=True)
    ids = set(user.business_access.values_list("business_id", flat=True))
    if user.business_id:
        ids.add(user.business_id)
    return Business.objects.filter(id__in=ids, is_active=True)
