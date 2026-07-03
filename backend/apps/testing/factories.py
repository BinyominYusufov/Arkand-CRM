"""Общие factory_boy-фабрики для всех тестов backend."""
from decimal import Decimal

import factory
from django.utils import timezone
from factory.django import DjangoModelFactory
from faker import Faker

from apps.cash.models import CashOperation, CashRegister
from apps.core import roles as R
from apps.core.models import Business, BusinessAccess, Holding, Role, RolePermission, User
from apps.finance.models import ExpenseCategory, Transaction
from apps.payroll.models import Employee, PayrollRun, SalaryScheme
from apps.settlements.models import Barter, Debt, DebtSettlement, Transfer

fake = Faker("ru_RU")


class HoldingFactory(DjangoModelFactory):
    class Meta:
        model = Holding

    name = "ARKAND"


class BusinessFactory(DjangoModelFactory):
    class Meta:
        model = Business

    name = factory.Sequence(lambda n: f"Бизнес {n}")
    code = factory.Sequence(lambda n: f"biz-{n}")
    kind = Business.Kind.FACTORY
    is_active = True


class UserFactory(DjangoModelFactory):
    class Meta:
        model = User

    username = factory.Sequence(lambda n: f"user{n}")
    email = factory.Sequence(lambda n: f"user{n}@arkand.tj")
    full_name = factory.LazyFunction(lambda: fake.name())
    role = R.ACCOUNTANT
    is_active = True

    @factory.post_generation
    def password(obj, create, extracted, **kwargs):
        obj.set_password(extracted or "arkand2026")
        if create:
            obj.save()


class ChiefFactory(UserFactory):
    role = R.CHIEF_ACCOUNTANT


class AccountantFactory(UserFactory):
    role = R.ACCOUNTANT


class CashierFactory(UserFactory):
    role = R.CASHIER


class OwnerFactory(UserFactory):
    role = R.OWNER


class BusinessAccessFactory(DjangoModelFactory):
    class Meta:
        model = BusinessAccess

    user = factory.SubFactory(UserFactory)
    business = factory.SubFactory(BusinessFactory)


class ExpenseCategoryFactory(DjangoModelFactory):
    class Meta:
        model = ExpenseCategory
        django_get_or_create = ("code",)

    name = factory.Sequence(lambda n: f"Категория {n}")
    code = factory.Sequence(lambda n: f"cat-{n}")


class TransactionFactory(DjangoModelFactory):
    class Meta:
        model = Transaction

    business = factory.SubFactory(BusinessFactory)
    kind = Transaction.Kind.INCOME
    amount = Decimal("1000.00")
    method = Transaction.Method.CASH
    status = Transaction.Status.PENDING
    occurred_at = factory.LazyFunction(timezone.now)


class CashRegisterFactory(DjangoModelFactory):
    class Meta:
        model = CashRegister

    name = factory.Sequence(lambda n: f"Касса {n}")
    business = factory.SubFactory(BusinessFactory)
    turnover_limit = Decimal("50000.00")
    is_active = True


class CashOperationFactory(DjangoModelFactory):
    class Meta:
        model = CashOperation

    register = factory.SubFactory(CashRegisterFactory)
    direction = CashOperation.Direction.IN
    method = CashOperation.Method.CASH
    amount = Decimal("500.00")
    occurred_at = factory.LazyFunction(timezone.now)


class TransferFactory(DjangoModelFactory):
    class Meta:
        model = Transfer

    from_business = factory.SubFactory(BusinessFactory)
    to_business = factory.SubFactory(BusinessFactory)
    amount = Decimal("5000.00")
    status = Transfer.Status.PENDING


class DebtFactory(DjangoModelFactory):
    class Meta:
        model = Debt

    debtor = factory.SubFactory(BusinessFactory)
    creditor = factory.SubFactory(BusinessFactory)
    amount = Decimal("5000.00")
    status = Debt.Status.OPEN


class BarterFactory(DjangoModelFactory):
    class Meta:
        model = Barter

    business_a = factory.SubFactory(BusinessFactory)
    business_b = factory.SubFactory(BusinessFactory)
    description = "Тестовый бартер"
    value = Decimal("3000.00")
    controlled_by = factory.SubFactory(AccountantFactory)
    status = Barter.Status.ACTIVE


class EmployeeFactory(DjangoModelFactory):
    class Meta:
        model = Employee

    full_name = factory.LazyFunction(lambda: fake.name())
    business = factory.SubFactory(BusinessFactory)
    salary_type = Employee.SalaryType.OBJECTIVE
    is_salesperson = False
    is_active = True


class SalarySchemeFactory(DjangoModelFactory):
    class Meta:
        model = SalaryScheme

    employee = factory.SubFactory(EmployeeFactory)
    scheme_type = SalaryScheme.SchemeType.FIXED
    config = {"base": 3000}
    is_active = True


class PayrollRunFactory(DjangoModelFactory):
    class Meta:
        model = PayrollRun

    year = 2026
    month = 5
    status = PayrollRun.Status.DRAFT
