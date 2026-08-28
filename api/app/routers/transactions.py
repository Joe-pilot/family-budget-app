import datetime as dt
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import select, extract

from ..db import get_db
from ..models import Category, Transaction
from ..schemas import TransactionIn, TransactionOut
from ..auth import require_api_key

router = APIRouter(prefix="/api/transactions", tags=["transactions"])


@router.get("", response_model=list[TransactionOut])
def list_transactions(
    year: int | None = Query(default=None, ge=2000, le=2100),
    month: int | None = Query(default=None, ge=1, le=12),
    category: str | None = Query(default=None, max_length=64),
    limit: int = Query(default=200, ge=1, le=500),
    db: Session = Depends(get_db),
):
    stmt = select(Transaction).order_by(Transaction.date.desc(), Transaction.id.desc())
    if year:
        stmt = stmt.where(extract("year", Transaction.date) == year)
    if month:
        stmt = stmt.where(extract("month", Transaction.date) == month)
    if category:
        stmt = stmt.where(Transaction.category == category)
    stmt = stmt.limit(limit)
    return db.scalars(stmt).all()


@router.post("", response_model=TransactionOut, dependencies=[Depends(require_api_key)])
def create_transaction(body: TransactionIn, db: Session = Depends(get_db)):
    category = db.scalar(
        select(Category).where(
            Category.category == body.category,
            Category.subcategory == body.subcategory,
        )
    )
    if not category or category.type != body.type:
        raise HTTPException(status_code=422, detail="Invalid type/category/subcategory combination")
    txn = Transaction(**body.model_dump())
    db.add(txn)
    db.commit()
    db.refresh(txn)
    return txn


@router.delete("/{txn_id}", dependencies=[Depends(require_api_key)])
def delete_transaction(txn_id: int, db: Session = Depends(get_db)):
    txn = db.get(Transaction, txn_id)
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")
    db.delete(txn)
    db.commit()
    return {"deleted": txn_id}
