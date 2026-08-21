import datetime as dt
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import select, extract

from ..db import get_db
from ..models import Transaction
from ..schemas import TransactionIn, TransactionOut
from ..auth import require_api_key

router = APIRouter(prefix="/api/transactions", tags=["transactions"])


@router.get("", response_model=list[TransactionOut])
def list_transactions(
    year: int | None = Query(default=None),
    month: int | None = Query(default=None),
    category: str | None = Query(default=None),
    limit: int = Query(default=200, le=2000),
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
