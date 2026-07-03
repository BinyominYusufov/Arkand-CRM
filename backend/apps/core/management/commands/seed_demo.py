"""seed_demo — наполняет весь проект богатыми реалистичными данными.

Принципы (ТЗ, раздел 12):
- сидер зовёт ТЕ ЖЕ сервисы, что и API — данные проходят инварианты и аудит;
- Faker/random с фиксированным seed — прогоны воспроизводимы;
- 6 месяцев истории с сезонностью, все страницы и отчёты заполнены.
"""
import random
from datetime import datetime, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from faker import Faker

from apps.audit.models import AuditLog
from apps.cash import services as cash_services
from apps.cash.models import CashOperation, CashRegister
from apps.core import rbac, roles as R
from apps.core.models import (
    Business,
    BusinessAccess,
    Holding,
    Role,
    RolePermission,
    User,
)
from apps.finance import services as finance_services
from apps.finance.models import ExpenseCategory, Transaction
from apps.payroll import services as payroll_services
from apps.payroll.models import Employee, SalaryScheme
from apps.settlements import services as settlements_services
from apps.settlements.models import Debt

PASSWORD = "arkand2026"
SEED = 20260703

D = Decimal


def month_start(dt: datetime, back: int) -> datetime:
    """Первое число месяца `back` месяцев назад от dt (aware)."""
    total = dt.year * 12 + dt.month - 1 - back
    year, month0 = divmod(total, 12)
    return dt.replace(
        year=year, month=month0 + 1, day=1, hour=9, minute=0, second=0, microsecond=0
    )


class Command(BaseCommand):
    help = "Наполняет базу демо-данными ARKAND (идемпотентно не является — на чистую БД)"

    @transaction.atomic
    def handle(self, *args, **options):
        if User.objects.exists():
            self.stdout.write(self.style.WARNING(
                "База не пуста — seed_demo рассчитан на чистую БД. Прерываю."
            ))
            return

        random.seed(SEED)
        fake = Faker("ru_RU")
        Faker.seed(SEED)
        now = timezone.localtime()

        # --- Холдинг, роли, права (Часть 0) ---
        holding = Holding.objects.create(
            name="ARKAND",
            requisites={"legal_name": "Холдинг ARKAND", "city": "Душанбе",
                        "phone": "+992 988 64 55 43"},
        )
        for code, name in R.ALL_ROLES.items():
            role = Role.objects.create(code=code, name=name)
            for perm in rbac.DEFAULT_ROLE_PERMISSIONS.get(code, ()):
                RolePermission.objects.create(role=role, perm=perm)

        # --- Бизнесы ---
        almosi = Business.objects.create(
            holding=holding, name="Завод Алмосӣ", code="almosi", kind="factory"
        )
        somon = Business.objects.create(
            holding=holding, name="Завод Сомон", code="somon", kind="factory"
        )
        stroy = Business.objects.create(
            holding=holding, name="Строй-Инвест", code="stroy-invest", kind="developer"
        )
        buro = Business.objects.create(
            holding=holding, name="Проект-Бюро", code="proekt-buro", kind="design"
        )
        businesses = [almosi, somon, stroy, buro]

        # --- Пользователи ---
        def mk_user(email, full_name, role, business=None, superuser=False):
            u = User(
                username=email.split("@")[0],
                email=email,
                full_name=full_name,
                role=role,
                business=business,
                is_staff=superuser,
                is_superuser=superuser,
            )
            u.set_password(PASSWORD)
            u.save()
            return u

        chief = mk_user("nigina@arkand.tj", "Нигина Рахимова", R.CHIEF_ACCOUNTANT)
        acc1 = mk_user("firuz@arkand.tj", "Фируз Каримов", R.ACCOUNTANT)
        acc2 = mk_user("manizha@arkand.tj", "Манижа Азимова", R.ACCOUNTANT)
        cash_stroy_u = mk_user("jamshed@arkand.tj", "Джамшед Холов", R.CASHIER, stroy)
        cash_buro_u = mk_user("farrukh@arkand.tj", "Фаррух Назаров", R.CASHIER, buro)
        cash_almosi_u = mk_user("sino@arkand.tj", "Сино Раджабов", R.CASHIER, almosi)
        cash_somon_u = mk_user("dilnoza@arkand.tj", "Дилноза Юсупова", R.CASHIER, somon)
        owner1 = mk_user("owner@arkand.tj", "Махмадсаид Бобоев", R.OWNER)
        owner2 = mk_user("umed@arkand.tj", "Умед Гафуров", R.OWNER)
        mk_user("rustam@arkand.tj", "Рустам Шарипов", R.MANAGER, stroy)
        mk_user("admin@arkand.tj", "Администратор", R.OWNER, superuser=True)

        # Ролевая матрица доступа к бизнесам (Часть 0, BusinessAccess).
        for u in (cash_stroy_u, cash_buro_u, cash_almosi_u, cash_somon_u):
            BusinessAccess.objects.create(user=u, business=u.business)
        BusinessAccess.objects.create(
            user=User.objects.get(email="rustam@arkand.tj"), business=stroy
        )

        # --- Категории расходов (ФНС-02) ---
        categories = {}
        for code, name in [
            ("raw_materials", "Закупка сырья/материалов"),
            ("salary", "Зарплата"),
            ("taxes", "Налоги"),
            ("electricity", "Электроэнергия"),
            ("repairs", "Ремонт техники"),
            ("transport", "Транспорт"),
            ("other", "Прочее"),
        ]:
            categories[code] = ExpenseCategory.objects.create(code=code, name=name)

        # --- Кассы (КАС-01) ---
        reg_stroy = CashRegister.objects.create(
            name="Касса Строй-Инвест", business=stroy, turnover_limit=D("80000")
        )
        reg_buro = CashRegister.objects.create(
            name="Касса Проект-Бюро", business=buro, turnover_limit=D("40000")
        )
        reg_almosi = CashRegister.objects.create(
            name="Операторская касса", business=almosi, turnover_limit=D("120000")
        )
        reg_somon = CashRegister.objects.create(
            name="Касса продаж", business=somon, turnover_limit=D("200000")
        )
        reg_stroy.members.add(cash_stroy_u)
        reg_buro.members.add(cash_buro_u)
        reg_almosi.members.add(cash_almosi_u)
        reg_somon.members.add(cash_somon_u)

        # --- Приходы/расходы: 6 месяцев истории с сезонностью (ФНС-01…04) ---
        income_profiles = {
            almosi.pk: dict(ops=(8, 13), amount=(30000, 120000),
                            notes=["Продажа кирпича, партия №{}", "Отгрузка блоков, накладная №{}",
                                   "Продажа цемента, договор №{}"]),
            somon.pk: dict(ops=(6, 10), amount=(20000, 90000),
                           notes=["Продажа профнастила, счёт №{}", "Отгрузка арматуры №{}"]),
            stroy.pk: dict(ops=(4, 9), amount=(150000, 400000),
                           notes=["Продажа квартиры №{}", "Взнос по ДДУ, договор №{}"]),
            buro.pk: dict(ops=(5, 9), amount=(20000, 60000),
                          notes=["Оплата за проект, договор №{}", "Авторский надзор, акт №{}"]),
        }
        expense_profiles = [
            ("raw_materials", (15000, 90000), 0.30, "Закупка сырья, счёт №{}"),
            ("salary", (20000, 60000), 0.12, "Выплата зарплаты за месяц"),
            ("taxes", (5000, 18000), 0.10, "Налоговый платёж №{}"),
            ("electricity", (2000, 9000), 0.12, "Электроэнергия, счёт №{}"),
            ("repairs", (1000, 12000), 0.12, "Ремонт техники, заказ-наряд №{}"),
            ("transport", (500, 4000), 0.16, "Транспортные расходы №{}"),
            ("other", (200, 2500), 0.08, "Хозяйственные расходы"),
        ]
        # Сезонность: заводы растут к лету, застройщик — весной, бюро стабильно.
        season = {
            almosi.pk: [0.8, 0.9, 1.0, 1.1, 1.25, 1.3],
            somon.pk: [0.7, 0.8, 1.0, 1.15, 1.2, 1.35],
            stroy.pk: [0.9, 1.1, 1.3, 1.2, 1.0, 1.1],
            buro.pk: [1.0, 0.95, 1.05, 1.0, 1.1, 1.05],
        }

        accountants = [chief, acc1, acc2]
        pending_left = 8  # часть приходов остаётся pending (сценарий ФНС-01)

        for back in range(5, -1, -1):
            m_start = month_start(now, back)
            season_idx = 5 - back
            days_in_month = 28 if back > 0 else max(now.day - 1, 1)
            for b in businesses:
                prof = income_profiles[b.pk]
                k = season[b.pk][season_idx]
                n_inc = round(random.randint(*prof["ops"]) * k)
                # В прошлом месяце у застройщика >10 продаж — для ступени ЗРП-05.
                if b.pk == stroy.pk and back == 1:
                    n_inc = 12
                for _ in range(max(n_inc, 2)):
                    occurred = m_start + timedelta(
                        days=random.randint(0, days_in_month - 1),
                        hours=random.randint(0, 8),
                        minutes=random.randint(0, 59),
                    )
                    amount = D(random.randint(*prof["amount"])).quantize(D("0.01"))
                    note = random.choice(prof["notes"]).format(random.randint(100, 999))
                    actor = random.choice(accountants)
                    tx = finance_services.create_income(
                        actor, business=b, amount=amount,
                        method=random.choice(["cash", "transfer"]),
                        occurred_at=occurred, note=note,
                    )
                    # Свежие приходы оставляем pending для сценария подтверждения.
                    if back == 0 and pending_left > 0 and random.random() < 0.5:
                        pending_left -= 1
                    else:
                        finance_services.confirm_income(
                            random.choice([chief, acc1]), transaction_id=tx.pk
                        )
                for code, (lo, hi), prob_k, note_tpl in expense_profiles:
                    n_exp = max(1, round(random.randint(2, 5) * prob_k * 10 * k / 3))
                    for _ in range(n_exp):
                        occurred = m_start + timedelta(
                            days=random.randint(0, days_in_month - 1),
                            hours=random.randint(0, 8),
                        )
                        finance_services.create_expense(
                            random.choice(accountants),
                            business=b,
                            category=categories[code],
                            amount=D(random.randint(lo, hi)).quantize(D("0.01")),
                            method=random.choice(["cash", "transfer"]),
                            occurred_at=occurred,
                            note=note_tpl.format(random.randint(100, 999)),
                        )

        # --- Операции касс (КАС-02/03): 3 месяца, лимиты частично выбраны ---
        registers = {
            reg_stroy.pk: (reg_stroy, cash_stroy_u),
            reg_buro.pk: (reg_buro, cash_buro_u),
            reg_almosi.pk: (reg_almosi, cash_almosi_u),
            reg_somon.pk: (reg_somon, cash_somon_u),
        }
        for reg, cashier in registers.values():
            for back in range(2, -1, -1):
                m_start = month_start(now, back)
                days_in_month = 26 if back > 0 else max(now.day - 1, 1)
                limit = reg.turnover_limit
                # Текущий месяц: Проект-Бюро близко к лимиту (~88%).
                target = limit * (
                    D("0.88") if (back == 0 and reg.pk == reg_buro.pk)
                    else D(str(random.uniform(0.35, 0.6)))
                )
                turnover = D("0")
                balance = D("0")
                while turnover < target:
                    amount = D(random.randint(500, 6000)).quantize(D("0.01"))
                    if turnover + amount > limit:
                        break
                    direction = "in" if (balance < amount or random.random() < 0.65) else "out"
                    op = cash_services.create_cash_operation(
                        cashier,
                        register=reg,
                        direction=direction,
                        method=random.choice(["cash", "transfer"]),
                        amount=amount,
                        occurred_at=m_start + timedelta(
                            days=random.randint(0, days_in_month - 1),
                            hours=random.randint(0, 9),
                        ),
                        note=random.choice(
                            ["Выручка за день", "Инкассация", "Оплата поставщику",
                             "Возврат подотчёта", "Аванс на закупку"]
                        ),
                    )
                    turnover += amount
                    balance += amount if direction == "in" else -amount

        # Касса «Операторская» превышала лимит: лимит снизили после оборота.
        AuditLog.record(
            chief, "cash_register.limit_changed", reg_almosi,
            before={"turnover_limit": str(reg_almosi.turnover_limit)},
            after={"turnover_limit": "35000.00"},
        )
        CashRegister.objects.filter(pk=reg_almosi.pk).update(turnover_limit=D("35000"))

        # --- Взаиморасчёты (БАР-01…04, ХОЛ-30…33) ---
        sv = settlements_services
        # Обычные передачи → авто-долги.
        t1 = sv.create_transfer(acc1, from_business=almosi, to_business=stroy,
                                amount=D("30000"), note="Кирпич для объекта «Сафо»")
        sv.approve_transfer(transfer_id=t1.pk, actor=chief)
        t2 = sv.create_transfer(acc2, from_business=stroy, to_business=almosi,
                                amount=D("18000"), note="Возврат материалов")
        sv.approve_transfer(transfer_id=t2.pk, actor=chief)  # встречный долг (неттинг)
        t3 = sv.create_transfer(acc1, from_business=buro, to_business=somon,
                                amount=D("12000"), note="Оплата за металлоконструкции")
        sv.approve_transfer(transfer_id=t3.pk, actor=acc2)
        # Долг, закрытый возвратом.
        t4 = sv.create_transfer(acc2, from_business=somon, to_business=buro,
                                amount=D("9000"), note="Аванс за проект склада")
        d4 = sv.approve_transfer(transfer_id=t4.pk, actor=chief)
        sv.settle_debt(chief, debt_id=d4.pk, method="return",
                       note="Возврат по акту сверки")
        # Частично погашенный долг.
        t5 = sv.create_transfer(acc1, from_business=almosi, to_business=buro,
                                amount=D("20000"), note="Материалы для офиса")
        d5 = sv.approve_transfer(transfer_id=t5.pk, actor=chief)
        sv.settle_debt(acc1, debt_id=d5.pk, method="return", amount=D("8000"),
                       note="Частичный возврат")
        # Просроченный долг (ХОЛ-33): старше 30 дней.
        t6 = sv.create_transfer(acc2, from_business=somon, to_business=stroy,
                                amount=D("25000"), note="Арматура на объект")
        d6 = sv.approve_transfer(transfer_id=t6.pk, actor=chief)
        Debt.objects.filter(pk=d6.pk).update(created_at=now - timedelta(days=45))
        # Передача СВЕРХ порога ХОЛ-32 — ждёт одобрения владельцем.
        sv.create_transfer(acc1, from_business=stroy, to_business=almosi,
                           amount=D("75000"), note="Финансирование новой линии")
        # Передача сверх порога, уже одобренная владельцем.
        t8 = sv.create_transfer(acc2, from_business=stroy, to_business=somon,
                                amount=D("90000"), note="Предоплата за металл на год")
        sv.approve_transfer(transfer_id=t8.pk, actor=owner1)
        # Обычная передача в ожидании.
        sv.create_transfer(acc1, from_business=buro, to_business=almosi,
                           amount=D("6000"), note="Оплата испытаний образцов")
        # Отклонённая передача.
        t10 = sv.create_transfer(acc2, from_business=somon, to_business=almosi,
                                 amount=D("14000"), note="Дублирующая заявка")
        sv.reject_transfer(chief, transfer_id=t10.pk)

        # Бартеры (БАР-04, ХОЛ-33).
        sv.create_barter(acc1, business_a=almosi, business_b=stroy,
                         description="Кирпич в обмен на отделочные работы офиса",
                         value=D("15000"), controlled_by=acc1)
        b2 = sv.create_barter(acc2, business_a=somon, business_b=stroy,
                              description="Металлопрокат в обмен на помещение под склад",
                              value=D("10000"), controlled_by=acc2)
        # Бартер закрывает встречный долг (ХОЛ-33): долг stroy→somon из t8.
        debt_stroy_somon = Debt.objects.filter(
            debtor=somon, creditor=stroy, status="open"
        ).first()
        if debt_stroy_somon:
            sv.close_debt_with_barter(chief, barter_id=b2.pk, debt_id=debt_stroy_somon.pk)
        b3 = sv.create_barter(acc1, business_a=buro, business_b=almosi,
                              description="Проект пристройки в обмен на стройматериалы",
                              value=D("7000"), controlled_by=acc1)
        sv.complete_barter(acc1, barter_id=b3.pk)

        # --- Зарплата (ЗРП-01…05) ---
        def employee(full_name, business, position, salary_type, is_sales=False):
            return Employee.objects.create(
                full_name=full_name, business=business, position=position,
                salary_type=salary_type, is_salesperson=is_sales,
            )

        def scheme(emp, stype, config):
            return SalaryScheme.objects.create(
                employee=emp, scheme_type=stype, config=config
            )

        # Продажники заводов: ЗРП-04 (фикс + % от продаж). Цифры — примеры из seed.
        for b, names in [
            (almosi, ["Шерали Кодиров", "Заррина Мирзоева"]),
            (somon, ["Далер Хайдаров"]),
        ]:
            for name in names:
                e = employee(name, b, "Менеджер по продажам", "objective", True)
                scheme(e, "percent_of_sales", {"base": 3000, "percent": 10})
        # Продажники застройщика: ЗРП-05 (за квартиру со ступенью), оба режима.
        e = employee("Парвина Саидова", stroy, "Менеджер по продажам квартир",
                     "objective", True)
        scheme(e, "per_unit_tiered", {
            "base": 3000, "unit": "квартира", "tier_mode": "flat",
            "tiers": [{"upto": 10, "rate": 500}, {"upto": None, "rate": 1000}],
        })
        e = employee("Хуршед Насимов", stroy, "Старший менеджер продаж",
                     "objective", True)
        scheme(e, "per_unit_tiered", {
            "base": 3500, "unit": "квартира", "tier_mode": "marginal",
            "tiers": [{"upto": 10, "rate": 500}, {"upto": None, "rate": 1000}],
        })
        # Оклады: объектные и административные (ЗРП-02).
        fixed_staff = [
            ("Азиз Рахмонов", almosi, "Начальник цеха", "objective", 4200),
            ("Мехрубон Собиров", almosi, "Оператор линии", "objective", 2600),
            ("Гулноз Шарифова", somon, "Технолог", "objective", 3400),
            ("Комрон Убайдуллоев", stroy, "Прораб", "objective", 4800),
            ("Мадина Латипова", buro, "Ведущий инженер-проектировщик", "objective", 5200),
            ("Насиба Тошева", buro, "Архитектор", "objective", 4600),
            ("Сорбон Икромов", None, "Юрист головного офиса", "administrative", 3800),
            ("Тахмина Вализода", None, "HR-специалист", "administrative", 3200),
            ("Некруз Амиров", stroy, "Офис-менеджер", "administrative", 2400),
        ]
        for name, b, pos, stype, base in fixed_staff:
            e = employee(name, b, pos, stype)
            scheme(e, "fixed", {"base": base})

        # Расчёты: 3 утверждённых месяца + черновик текущего (ЗРП-01).
        for back in (3, 2, 1):
            m = month_start(now, back)
            run = payroll_services.run_payroll(chief, year=m.year, month=m.month)
            payroll_services.finalize_run(chief, run_id=run.pk)
        payroll_services.run_payroll(acc1, year=now.year, month=now.month)  # черновик

        # --- Итоги ---
        self.stdout.write(self.style.SUCCESS("\nSeed завершён. Данные:"))
        self.stdout.write(f"  Транзакции: {Transaction.objects.count()}")
        self.stdout.write(f"  Операции касс: {CashOperation.objects.count()}")
        self.stdout.write(f"  Долги: {Debt.objects.count()}")
        self.stdout.write(f"  Записи аудита: {AuditLog.objects.count()}")
        self.stdout.write(self.style.SUCCESS("\nПользователи (пароль у всех: %s)" % PASSWORD))
        for u in User.objects.order_by("id"):
            self.stdout.write(f"  {u.email:26} {u.role:18} {u.full_name}")
