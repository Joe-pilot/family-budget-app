from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select
import datetime as dt

from ..db import get_db
from ..models import Category, Transaction
from ..schemas import AgentRequest, AgentResponse, TransactionOut
from ..ollama_client import parse_message, ParseError
from ..auth import require_api_key

router = APIRouter(prefix="/api/agent", tags=["agent"])


@router.post("/log", response_model=AgentResponse, dependencies=[Depends(require_api_key)])
def agent_log(body: AgentRequest, db: Session = Depends(get_db)):
    categories = [(c.type, c.category, c.subcategory) for c in db.scalars(select(Category))]

    try:
        parsed = parse_message(body.text, categories)
    except ParseError as e:
        raise HTTPException(status_code=422, detail=e.message)

    created = []
    for t in parsed:
        try:
            txn_date = dt.date.fromisoformat(t["date"])
        except (ValueError, TypeError):
            txn_date = dt.date.today()
        txn = Transaction(
            date=txn_date, type=t["type"], category=t["category"], subcategory=t["subcategory"],
            description=t["description"], amount=t["amount"], payment_method=t["payment_method"],
            notes=t["notes"], source=body.source, created_by=body.created_by,
        )
        db.add(txn)
        created.append(txn)
    db.commit()
    for txn in created:
        db.refresh(txn)

    reply_lines = []
    for txn in created:
        sign = "+" if txn.type == "Income" else "−"
        reply_lines.append(f"{txn.date} · {txn.category} / {txn.subcategory} · {sign}{txn.amount} {txn.type}")

    return AgentResponse(
        transactions=[TransactionOut.model_validate(t) for t in created],
        reply="\n".join(reply_lines),
    )
