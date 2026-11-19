
import argparse
import sqlite3
import sys
from pathlib import Path
from typing import Sequence

import database, services


def format_money(amount: object) -> str:
    return f"₦{amount:,.2f}"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="A simple expense tracking application."
    )

    parser.add_argument(
        "--db",
        type=Path,
        default=Path("expenses.db"),
        help="Database file location",
    )

    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
    )

    add_parser = subparsers.add_parser(
        "add",
        help="Add a new expense",
    )

    add_parser.add_argument(
        "--amount",
        required=True,
        help="Expense amount",
    )

    add_parser.add_argument(
        "--category",
        required=True,
        help="Expense category",
    )

    add_parser.add_argument(
        "--description",
        default="",
        help="Expense description",
    )

    add_parser.add_argument(
        "--date",
        required=True,
        dest="expense_date",
        help="Expense date in YYYY-MM-DD format",
    )

    subparsers.add_parser(
        "list",
        help="List all expenses",
    )

    summary_parser = subparsers.add_parser(
        "summary",
        help="Show monthly expense summary",
    )

    summary_parser.add_argument(
        "--month",
        required=True,
        help="Month in YYYY-MM format",
    )

    delete_parser = subparsers.add_parser(
        "delete",
        help="Delete an expense",
    )

    delete_parser.add_argument(
        "--id",
        required=True,
        type=int,
        help="Expense ID",
    )

    return parser


def handle_add(args: argparse.Namespace, db_path: Path) -> None:
    expense = services.create_expense(
        amount=args.amount,
        category=args.category,
        description=args.description,
        expense_date=args.expense_date,
    )

    saved = services.save_expense(expense, db_path)

    print(f"Expense added successfully. ID: {saved.id}")


def handle_list(db_path: Path) -> None:
    expenses = services.get_expenses(db_path)

    if not expenses:
        print("No expenses found.")
        return

    print("\nYOUR EXPENSES")
    print("-" * 75)

    for expense in expenses:
        print(
            f"ID: {expense.id} | "
            f"{expense.expense_date} | "
            f"{expense.category} | "
            f"{format_money(expense.amount)} | "
            f"{expense.description}"
        )

    print("-" * 75)


def handle_summary(month: str, db_path: Path) -> None:
    summary = services.summarize_expenses(month, db_path)

    print(f"\nEXPENSE SUMMARY: {month}")
    print("-" * 40)

    total = sum(summary.values(), start=services.parse_amount("0"))

    if not summary:
        print("No expenses found for this month.")
        return

    for category, amount in summary.items():
        print(f"{category.title():20} {format_money(amount)}")

    print("-" * 40)
    print(f"{'TOTAL':20} {format_money(total)}")


def handle_delete(expense_id: int, db_path: Path) -> None:
    deleted = services.remove_expense(expense_id, db_path)

    if deleted:
        print(f"Expense {expense_id} deleted successfully.")
    else:
        print(f"Expense {expense_id} was not found.")


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    db_path: Path = args.db

    try:
        database.initialize_database(db_path)

        if args.command == "add":
            handle_add(args, db_path)

        elif args.command == "list":
            handle_list(db_path)

        elif args.command == "summary":
            handle_summary(args.month, db_path)

        elif args.command == "delete":
            handle_delete(args.id, db_path)

        return 0

    except (ValueError, sqlite3.Error, OSError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
