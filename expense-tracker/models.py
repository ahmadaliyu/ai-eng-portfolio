from dataclasses import dataclass
from datetime import date
from decimal import Decimal

@dataclass
class Expense:
    id: int | None
    amount: Decimal
    description: str
    expense_date: date
    category: str

    def __post_init__(self) -> None:
        if not self.amount.is_finite():
            raise ValueError("Amount must be finite number")
        if self.amount <= 0:
            raise ValueError("Amount must be greater than zero")
        if self.amount != self.amount.quantize(Decimal('0.01')):
            raise ValueError("Amount cannot have more than two decimal places")
        if not self.category.strip():
            raise ValueError("Category cannot be empty")