from sqlalchemy.orm import Session
from sqlalchemy import select
from .models import Category, BudgetItem
from .catalog import CATS


def seed_catalog(db: Session) -> None:
    existing = {(c.category, c.subcategory) for c in db.scalars(select(Category))}
    existing_budget = {(b.category, b.subcategory) for b in db.scalars(select(BudgetItem))}

    added = 0
    for t, c, s in CATS:
        if (c, s) not in existing:
            db.add(Category(type=t, category=c, subcategory=s))
            added += 1
        if (c, s) not in existing_budget:
            db.add(BudgetItem(type=t, category=c, subcategory=s, monthly_amount=0))

    if added:
        db.commit()
