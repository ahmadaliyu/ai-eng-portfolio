
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

import database
from models import Expense


def parse_date(value: str) -> date:
    try:
        parsed = date.fromisoformat(value)
    except ValueError as error:
        raise ValueError(
            "Invalid date. Use YYYY-MM-DD."
        ) from error

    if parsed.isoformat() != value:
        raise ValueError("Date must use YYYY-MM-DD format")

    return parsed


def parse_month(value: str) -> str:
    try:
        parsed = date.fromisoformat(f"{value}-01")
    except ValueError as error:
        raise ValueError(
            "Invalid month. Use YYYY-MM."
        ) from error

    if parsed.strftime("%Y-%m") != value:
        raise ValueError("Month must use YYYY-MM format")

    return value


def parse_amount(value: str) -> Decimal:
    try:
        amount = Decimal(value)
    except InvalidOperation as error:
        raise ValueError("Amount must be a valid number") from error

    if not amount.is_finite():
        raise ValueError("Amount must be a finite number")

    if amount <= 0:
        raise ValueError("Amount must be greater than zero")

    if amount != amount.quantize(Decimal("0.01")):
        raise ValueError("Amount cannot have more than 2 decimal places")

    return amount


def create_expense(
    amount: str,
    category: str,
    description: str,
    expense_date: str,
) -> Expense:
    if not category.strip():
        raise ValueError("Category cannot be empty")

    return Expense(
        id=None,
        amount=parse_amount(amount),
        category=category.strip().lower(),
        description=description.strip(),
        expense_date=parse_date(expense_date),
    )


def save_expense(
    expense: Expense,
    db_path: Path,
) -> Expense:
    return database.add_expense(expense, db_path)


def get_expenses(db_path: Path) -> list[Expense]:
    return database.list_expenses(db_path)


def remove_expense(expense_id: int, db_path: Path) -> bool:
    if expense_id <= 0:
        raise ValueError("Expense ID must be positive")

    return database.delete_expense(expense_id, db_path)


def summarize_expenses(
    month: str,
    db_path: Path,
) -> dict[str, Decimal]:
    validated_month = parse_month(month)

    return database.get_monthly_summary(
        validated_month,
        db_path,
    )
