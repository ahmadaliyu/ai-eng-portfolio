
import sqlite3
from contextlib import closing
from dataclasses import replace
from datetime import date
from decimal import Decimal
from pathlib import Path

from models import Expense


def get_connection(db_path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database(db_path: Path) -> None:
    with closing(get_connection(db_path)) as connection:
        with connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS expenses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    amount_kobo INTEGER NOT NULL,
                    category TEXT NOT NULL,
                    description TEXT NOT NULL,
                    expense_date TEXT NOT NULL
                )
                """
            )


def add_expense(
    expense: Expense,
    db_path: Path,
) -> Expense:
    amount_kobo = int(expense.amount * Decimal("100"))

    with closing(get_connection(db_path)) as connection:
        with connection:
            cursor = connection.execute(
                """
                INSERT INTO expenses (
                    amount_kobo,
                    category,
                    description,
                    expense_date
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    amount_kobo,
                    expense.category,
                    expense.description,
                    expense.expense_date.isoformat(),
                ),
            )

            expense_id = cursor.lastrowid

            if expense_id is None:
                raise RuntimeError("Failed to create expense")

            return replace(expense, id=expense_id)


def list_expenses(db_path: Path) -> list[Expense]:
    with closing(get_connection(db_path)) as connection:
        rows = connection.execute(
            """
            SELECT id, amount_kobo, category, description, expense_date
            FROM expenses
            ORDER BY expense_date DESC, id DESC
            """
        ).fetchall()

    return [
        Expense(
            id=int(row["id"]),
            amount=Decimal(int(row["amount_kobo"])) / Decimal("100"),
            category=str(row["category"]),
            description=str(row["description"]),
            expense_date=date.fromisoformat(
                str(row["expense_date"])
            ),
        )
        for row in rows
    ]


def delete_expense(expense_id: int, db_path: Path) -> bool:
    with closing(get_connection(db_path)) as connection:
        with connection:
            cursor = connection.execute(
                "DELETE FROM expenses WHERE id = ?",
                (expense_id,),
            )

            return cursor.rowcount > 0


def get_monthly_summary(
    month: str,
    db_path: Path,
) -> dict[str, Decimal]:
    with closing(get_connection(db_path)) as connection:
        rows = connection.execute(
            """
            SELECT category, SUM(amount_kobo) AS total
            FROM expenses
            WHERE substr(expense_date, 1, 7) = ?
            GROUP BY category
            ORDER BY category
            """,
            (month,),
        ).fetchall()

    return {
        str(row["category"]): (
            Decimal(int(row["total"])) / Decimal("100")
        )
        for row in rows
    }
