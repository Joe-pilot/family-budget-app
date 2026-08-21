import datetime as dt
from pydantic import BaseModel, Field, field_validator
from .catalog import VALID_TYPES


class CategoryOut(BaseModel):
    id: int
    type: str
    category: str
    subcategory: str

    class Config:
        from_attributes = True


class BudgetItemOut(BaseModel):
    id: int
    type: str
    category: str
    subcategory: str
    monthly_amount: float

    class Config:
        from_attributes = True


class BudgetItemUpdate(BaseModel):
    monthly_amount: float = Field(ge=0)


class TransactionIn(BaseModel):
    date: dt.date
    type: str
    category: str
    subcategory: str
    description: str = ""
    amount: float = Field(gt=0)
    payment_method: str = ""
    notes: str = ""
    source: str = "web"
    created_by: str = ""

    @field_validator("type")
    @classmethod
    def valid_type(cls, v):
        if v not in VALID_TYPES:
            raise ValueError(f"type must be one of {VALID_TYPES}")
        return v


class TransactionOut(BaseModel):
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

    class Config:
        from_attributes = True


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


class AgentRequest(BaseModel):
    text: str
    source: str = "agent"
    created_by: str = ""


class AgentResponse(BaseModel):
    transactions: list[TransactionOut]
    reply: str
