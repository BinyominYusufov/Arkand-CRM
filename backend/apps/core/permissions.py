"""DRF-права поверх data-driven RBAC (Часть 0, apps.core.rbac).

Классы тонкие: проверяют код права; «своё/чужое» дополнительно
режется на уровне queryset в selectors (изоляция КАС-04).
"""
from rest_framework.permissions import SAFE_METHODS, BasePermission

from . import rbac


class HasPerm(BasePermission):
    """Базовый класс: требуемое право в атрибуте perm."""

    perm: str = ""
    message = "Недостаточно прав"

    def has_permission(self, request, view):
        return rbac.user_has_perm(request.user, self.perm)


class ReadWritePerm(BasePermission):
    """SAFE-методы — perm_read, мутации — perm_write."""

    perm_read: str = ""
    perm_write: str = ""
    message = "Недостаточно прав"

    def has_permission(self, request, view):
        perm = self.perm_read if request.method in SAFE_METHODS else self.perm_write
        return rbac.user_has_perm(request.user, perm)


# --- Финансы: финотдел пишет, владелец читает ---
class FinanceSection(ReadWritePerm):
    perm_read = rbac.PERM_FINANCE_VIEW
    perm_write = rbac.PERM_FINANCE_MANAGE


class CanApproveFinance(HasPerm):
    perm = rbac.PERM_FINANCE_APPROVE
    message = "Подтверждать приходы могут финотдел и владельцы"


# --- Кассы ---
class CashSection(ReadWritePerm):
    perm_read = rbac.PERM_CASH_VIEW
    perm_write = rbac.PERM_CASH_OPERATE


class CanManageCashRegisters(ReadWritePerm):
    perm_read = rbac.PERM_CASH_VIEW
    perm_write = rbac.PERM_CASH_MANAGE


class IsCashRegisterMember(BasePermission):
    """Object-level: касса видна членам; финотдел/владельцы видят все."""

    message = "Чужая касса недоступна"

    def has_object_permission(self, request, view, obj):
        u = request.user
        if rbac.user_has_perm(u, rbac.PERM_CASH_VIEW_ALL):
            return True
        register = getattr(obj, "register", obj)  # CashOperation или CashRegister
        return register.members.filter(pk=u.pk).exists()


# --- Взаиморасчёты ---
class SettlementsSection(ReadWritePerm):
    perm_read = rbac.PERM_SETTLEMENTS_VIEW
    perm_write = rbac.PERM_SETTLEMENTS_MANAGE


class CanApproveSettlements(HasPerm):
    perm = rbac.PERM_SETTLEMENTS_APPROVE
    message = "Одобрять передачи могут финотдел и владельцы"


# --- Зарплата ---
class PayrollSection(ReadWritePerm):
    perm_read = rbac.PERM_PAYROLL_VIEW
    perm_write = rbac.PERM_PAYROLL_MANAGE


# --- Отчёты, аудит, overlay (Часть 7), справочники ---
class CanViewReports(HasPerm):
    perm = rbac.PERM_REPORTS_VIEW


class CanViewAudit(HasPerm):
    perm = rbac.PERM_AUDIT_VIEW


class OwnerOverlay(HasPerm):
    perm = rbac.PERM_OVERLAY_VIEW
    message = "Консолидация доступна только владельцам"


class BusinessesSection(ReadWritePerm):
    """Чтение — любой аутентифицированный, мутации — business.manage."""

    perm_write = rbac.PERM_BUSINESS_MANAGE

    def has_permission(self, request, view):
        u = request.user
        if not (u and u.is_authenticated):
            return False
        if request.method in SAFE_METHODS:
            return True
        return rbac.user_has_perm(u, self.perm_write)


class CanViewUsers(HasPerm):
    perm = rbac.PERM_USERS_VIEW
