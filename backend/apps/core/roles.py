"""Коды ролей холдинга (Часть 0).

# TODO: свериться с реальной Частью 0, когда появится ТЗ.
Роли хранятся в БД (модель Role), здесь — стабильные коды для сервисов/тестов.
"""

OWNER = "owner"
CHIEF_ACCOUNTANT = "chief_accountant"
ACCOUNTANT = "accountant"
CASHIER = "cashier"
MANAGER = "manager"
OPERATOR = "operator"
DIRECTOR = "director"

ALL_ROLES = {
    OWNER: "Владелец",
    CHIEF_ACCOUNTANT: "Главный бухгалтер",
    ACCOUNTANT: "Бухгалтер",
    CASHIER: "Кассир",
    MANAGER: "Менеджер",
    OPERATOR: "Оператор",
    DIRECTOR: "Директор",
}

# Финотдел: видит все деньги (КАС-04).
FINANCE_ROLES = (CHIEF_ACCOUNTANT, ACCOUNTANT)
