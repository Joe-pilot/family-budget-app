import calendar
import datetime as dt
from collections import defaultdict

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.orm import Session
from sqlalchemy import select, extract, func

from ..db import get_db
from ..models import Transaction, BudgetItem
from ..schemas import MonthlyTrendPoint, MonthDetail, CategoryLine, CategoryBreakdown

router = APIRouter(prefix="/api/summary", tags=["summary"])


def _actuals_by_key(db: Session, year: int, month: int | None = None) -> dict[tuple, float]:
    stmt = (
        select(Transaction.type, Transaction.category, Transaction.subcategory, func.sum(Transaction.amount))
        .where(extract("year", Transaction.date) == year)
    )
    if month:
        stmt = stmt.where(extract("month", Transaction.date) == month)
    stmt = stmt.group_by(Transaction.type, Transaction.category, Transaction.subcategory)
    out = {}
    for ttype, cat, sub, total in db.execute(stmt).all():
        out[(ttype, cat, sub)] = float(total or 0)
    return out


@router.get("/monthly", response_model=list[MonthlyTrendPoint])
def monthly_trend(year: int = Query(default=dt.date.today().year, ge=2000, le=2100), db: Session = Depends(get_db)):
    stmt = (
        select(
            extract("month", Transaction.date).label("m"),
            Transaction.type,
            func.sum(Transaction.amount),
        )
        .where(extract("year", Transaction.date) == year)
        .group_by("m", Transaction.type)
    )
    totals = defaultdict(lambda: defaultdict(float))
    for m, ttype, total in db.execute(stmt).all():
        totals[int(m)][ttype] = float(total or 0)

    points = []
    for m in range(1, 13):
        income = totals[m].get("Income", 0.0)
        expense = totals[m].get("Expense", 0.0)
        savings = totals[m].get("Savings", 0.0)
        points.append(MonthlyTrendPoint(
            year=year, month=m, month_name=calendar.month_name[m],
            income=income, expense=expense, savings=savings,
            net=income - expense - savings,
        ))
    return points


@router.get("/month/{year}/{month}", response_model=MonthDetail)
def month_detail(
    year: int = Path(ge=2000, le=2100),
    month: int = Path(ge=1, le=12),
    db: Session = Depends(get_db),
):
    budget_items = db.scalars(select(BudgetItem).order_by(BudgetItem.category, BudgetItem.subcategory)).all()
    actuals = _actuals_by_key(db, year, month)

    income, expense, savings = [], [], []
    totals = {"income_projected": 0.0, "income_actual": 0.0,
              "expense_projected": 0.0, "expense_actual": 0.0,
              "savings_projected": 0.0, "savings_actual": 0.0}

    for b in budget_items:
        actual = actuals.get((b.type, b.category, b.subcategory), 0.0)
        projected = float(b.monthly_amount)
        line = CategoryLine(category=b.category, subcategory=b.subcategory,
                             projected=projected, actual=actual, difference=projected - actual)
        if b.type == "Income":
            income.append(line)
            totals["income_projected"] += projected
            totals["income_actual"] += actual
        elif b.type == "Expense":
            expense.append(line)
            totals["expense_projected"] += projected
            totals["expense_actual"] += actual
        else:
            savings.append(line)
            totals["savings_projected"] += projected
            totals["savings_actual"] += actual

    totals["net_actual"] = totals["income_actual"] - totals["expense_actual"] - totals["savings_actual"]
    totals["net_projected"] = totals["income_projected"] - totals["expense_projected"] - totals["savings_projected"]
    totals["pct_income_spent"] = (totals["expense_actual"] / totals["income_actual"]) if totals["income_actual"] else 0.0
    totals["pct_income_saved"] = (totals["savings_actual"] / totals["income_actual"]) if totals["income_actual"] else 0.0

    return MonthDetail(year=year, month=month, income=income, expense=expense, savings=savings, totals=totals)


@router.get("/categories", response_model=list[CategoryBreakdown])
def ytd_category_breakdown(year: int = Query(default=dt.date.today().year, ge=2000, le=2100), db: Session = Depends(get_db)):
    stmt = (
        select(Transaction.category, func.sum(Transaction.amount))
        .where(extract("year", Transaction.date) == year, Transaction.type == "Expense")
        .group_by(Transaction.category)
    )
    rows = db.execute(stmt).all()
    total = sum(float(t or 0) for _, t in rows) or 1.0
    return [
        CategoryBreakdown(category=cat, ytd_actual=float(t or 0), pct_of_total=float(t or 0) / total)
        for cat, t in sorted(rows, key=lambda r: -(r[1] or 0))
    ]
