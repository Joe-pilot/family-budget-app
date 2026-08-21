from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select

from ..db import get_db
from ..models import BudgetItem
from ..schemas import BudgetItemOut, BudgetItemUpdate
from ..auth import require_api_key

router = APIRouter(prefix="/api/budget", tags=["budget"])


@router.get("", response_model=list[BudgetItemOut])
def list_budget(db: Session = Depends(get_db)):
    return db.scalars(select(BudgetItem).order_by(BudgetItem.category, BudgetItem.subcategory)).all()


@router.put("/{item_id}", response_model=BudgetItemOut, dependencies=[Depends(require_api_key)])
def update_budget(item_id: int, body: BudgetItemUpdate, db: Session = Depends(get_db)):
    item = db.get(BudgetItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Budget item not found")
    item.monthly_amount = body.monthly_amount
    db.commit()
    db.refresh(item)
    return item
