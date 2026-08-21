import datetime as dt
from sqlalchemy import String, Numeric, Date, DateTime, UniqueConstraint, Text
from sqlalchemy.orm import Mapped, mapped_column
from .db import Base


class Category(Base):
    __tablename__ = "categories"
    __table_args__ = (UniqueConstraint("category", "subcategory", name="uq_category_subcategory"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    type: Mapped[str] = mapped_column(String(16))
    category: Mapped[str] = mapped_column(String(64))
    subcategory: Mapped[str] = mapped_column(String(64))


class BudgetItem(Base):
    __tablename__ = "budget_items"
    __table_args__ = (UniqueConstraint("category", "subcategory", name="uq_budget_category_subcategory"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    type: Mapped[str] = mapped_column(String(16))
    category: Mapped[str] = mapped_column(String(64))
    subcategory: Mapped[str] = mapped_column(String(64))
    monthly_amount: Mapped[float] = mapped_column(Numeric(12, 2), default=0)


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    date: Mapped[dt.date] = mapped_column(Date, index=True)
    type: Mapped[str] = mapped_column(String(16))
    category: Mapped[str] = mapped_column(String(64), index=True)
    subcategory: Mapped[str] = mapped_column(String(64))
    description: Mapped[str] = mapped_column(Text, default="")
    amount: Mapped[float] = mapped_column(Numeric(12, 2))
    payment_method: Mapped[str] = mapped_column(String(32), default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    source: Mapped[str] = mapped_column(String(16), default="web")  # web | telegram | agent
    created_by: Mapped[str] = mapped_column(String(64), default="")  # telegram username/id, or "web"
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)
