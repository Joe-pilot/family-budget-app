import datetime as dt
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .catalog import PAYMENT_METHODS

MAX_AMOUNT = 999_999_999.99


class StrictInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class CategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    type: str
    category: str
    subcategory: str

class BudgetItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    type: str
    category: str
    subcategory: str
    monthly_amount: float

class BudgetItemUpdate(StrictInput):
    monthly_amount: float = Field(ge=0, le=MAX_AMOUNT, allow_inf_nan=False)


class TransactionIn(StrictInput):
    date: dt.date
    type: Literal["Income", "Expense", "Savings"]
    category: str = Field(min_length=1, max_length=64)
    subcategory: str = Field(min_length=1, max_length=64)
    description: str = Field(default="", max_length=500)
    amount: float = Field(gt=0, le=MAX_AMOUNT, allow_inf_nan=False)
    payment_method: Literal["", *PAYMENT_METHODS] = ""
    notes: str = Field(default="", max_length=1000)
    source: Literal["web", "telegram", "agent"] = "web"
    created_by: str = Field(default="", max_length=64)


class TransactionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    date: dt.date
    type: str
    category: str
    subcategory: str
    description: str
    amount: float
    payment_method: str
    notes: str
    source: str
    created_by: str
    created_at: dt.datetime

class MonthlyTrendPoint(BaseModel):
    year: int
    month: int
    month_name: str
    income: float
    expense: float
    savings: float
    net: float


class CategoryLine(BaseModel):
    category: str
    subcategory: str
    projected: float
    actual: float
    difference: float


class MonthDetail(BaseModel):
    year: int
    month: int
    income: list[CategoryLine]
    expense: list[CategoryLine]
    savings: list[CategoryLine]
    totals: dict


class CategoryBreakdown(BaseModel):
    category: str
    ytd_actual: float
    pct_of_total: float


class AgentRequest(StrictInput):
    text: str = Field(min_length=1, max_length=500)
    source: Literal["web", "telegram", "agent"] = "agent"
    created_by: str = Field(default="", max_length=64)


class AgentResponse(BaseModel):
    transactions: list[TransactionOut]
    reply: str
