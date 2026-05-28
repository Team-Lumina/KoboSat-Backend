from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db.database import get_db
from models.debt import Debt
from models.trader import Trader
from services.nostr_service import publish_debt_event
from services.sms import (
    send_debt_logged_confirmation,
    send_debt_reminder,
    send_debt_settled_confirmation,
)
from utils.validators import validate_phone, validate_amount

router = APIRouter()

class CreateDebtRequest(BaseModel):
    creditor_phone: str        # the trader who is owed money
    debtor_phone: str          # the customer who owes money
    amount_ngn: float
    description: str
    due_date: Optional[str] = None   # ISO format: "2026-06-15"


@router.post("/debts")
async def create_debt(
    req: CreateDebtRequest,
    db: Session = Depends(get_db),
):

    creditor = validate_phone(req.creditor_phone)
    if not creditor:
        raise HTTPException(
            status_code=400,
            detail="Invalid creditor phone number",
        )

    debtor = validate_phone(req.debtor_phone)
    if not debtor:
        raise HTTPException(
            status_code=400,
            detail="Invalid debtor phone number",
        )

    amount = validate_amount(req.amount_ngn)
    if not amount:
        raise HTTPException(
            status_code=400,
            detail="Invalid amount. Must be between ₦1 and ₦10,000,000",
        )

    if not req.description or not req.description.strip():
        raise HTTPException(
            status_code=400,
            detail="Description is required",
        )

    due_date = None
    if req.due_date:
        try:
            due_date = datetime.fromisoformat(req.due_date)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Invalid due_date format. Use ISO format: 2026-06-15",
            )

    trader = db.query(Trader).filter(
        Trader.phone_number == creditor
    ).first()

    if not trader:
        raise HTTPException(
            status_code=404,
            detail="Trader not found. Please register first.",
        )

    debt = Debt(
        creditor_phone=creditor,
        debtor_phone=debtor,
        amount_ngn=amount,
        description=req.description.strip(),
        due_date=due_date,
        status="pending",
    )
    db.add(debt)
    db.commit()
    db.refresh(debt)

    print(f"📋 Debt logged: {creditor} ← {debtor} ₦{amount:,.0f} ({req.description})")

    nostr_event_id = ""
    try:
        nostr_event_id = await publish_debt_event(
            privkey_hex=trader.nostr_privkey,
            pubkey_hex=trader.nostr_pubkey,
            debt_id=debt.debt_id,
            debtor_phone=debtor,
            amount_ngn=amount,
            description=req.description.strip(),
        )
        if nostr_event_id:
            debt.nostr_event_id = nostr_event_id
            db.commit()
    except Exception as e:
        print(f"⚠️  Nostr publish failed for debt {debt.debt_id[:8]}: {e}")

    try:
        await send_debt_logged_confirmation(
            trader_phone=creditor,
            debtor_phone=debtor,
            amount_ngn=amount,
            description=req.description.strip(),
        )
    except Exception as e:
        print(f"⚠️  SMS failed for debt confirmation: {e}")

    return {
        "message": "Debt logged successfully.",
        "debt_id": debt.debt_id,
        "creditor_phone": debt.creditor_phone,
        "debtor_phone": debt.debtor_phone,
        "amount_ngn": debt.amount_ngn,
        "description": debt.description,
        "status": debt.status,
        "due_date": debt.due_date.isoformat() if debt.due_date else None,
        "nostr_event_id": nostr_event_id,
        "nostr_link": (
            f"https://njump.me/{nostr_event_id}"
            if nostr_event_id else None
        ),
        "created_at": debt.created_at.isoformat(),
    }


@router.get("/debts/{phone}")
async def list_debts(
    phone: str,
    db: Session = Depends(get_db),
):

    validated_phone = validate_phone(phone)
    if not validated_phone:
        raise HTTPException(
            status_code=400,
            detail="Invalid phone number",
        )

    trader = db.query(Trader).filter(
        Trader.phone_number == validated_phone
    ).first()

    if not trader:
        raise HTTPException(
            status_code=404,
            detail="Trader not found.",
        )

    all_debts = (
        db.query(Debt)
        .filter(Debt.creditor_phone == validated_phone)
        .order_by(Debt.created_at.desc())
        .all()
    )

    outstanding = [d for d in all_debts if d.status in ("pending", "reminded")]
    total_outstanding_ngn = sum(d.amount_ngn for d in outstanding)

    def format_debt(d: Debt) -> dict:
        return {
            "debt_id": d.debt_id,
            "debtor_phone": d.debtor_phone,
            "amount_ngn": d.amount_ngn,
            "description": d.description,
            "status": d.status,
            "due_date": d.due_date.isoformat() if d.due_date else None,
            "nostr_event_id": d.nostr_event_id,
            "nostr_link": (
                f"https://njump.me/{d.nostr_event_id}"
                if d.nostr_event_id else None
            ),
            "created_at": d.created_at.isoformat(),
            "settled_at": (
                d.settled_at.isoformat() if d.settled_at else None
            ),
        }

    return {
        "phone_number": validated_phone,
        "total_outstanding_ngn": total_outstanding_ngn,
        "outstanding_count": len(outstanding),
        "total_count": len(all_debts),
        "debts": [format_debt(d) for d in all_debts],
    }


@router.patch("/debts/{debt_id}/settle")
async def settle_debt(
    debt_id: str,
    phone: str,
    db: Session = Depends(get_db),
):

    validated_phone = validate_phone(phone)
    if not validated_phone:
        raise HTTPException(
            status_code=400,
            detail="Invalid phone number",
        )

    debt = db.query(Debt).filter(
        Debt.debt_id == debt_id,
        Debt.creditor_phone == validated_phone,
    ).first()

    if not debt:
        raise HTTPException(
            status_code=404,
            detail="Debt not found or does not belong to this trader.",
        )

    if debt.status == "settled":
        raise HTTPException(
            status_code=400,
            detail="This debt is already settled.",
        )

    debt.status = "settled"
    debt.settled_at = datetime.utcnow()
    db.commit()
    db.refresh(debt)

    print(f"✅ Debt settled: {debt_id[:8]}... ₦{debt.amount_ngn:,.0f}")

    try:
        await send_debt_settled_confirmation(
            trader_phone=validated_phone,
            debtor_phone=debt.debtor_phone,
            amount_ngn=debt.amount_ngn,
        )
    except Exception as e:
        print(f"⚠️  SMS failed for settle confirmation: {e}")

    return {
        "message": "Debt marked as settled.",
        "debt_id": debt.debt_id,
        "amount_ngn": debt.amount_ngn,
        "status": debt.status,
        "settled_at": debt.settled_at.isoformat(),
    }


@router.post("/debts/{debt_id}/remind")
async def send_reminder(
    debt_id: str,
    phone: str,
    db: Session = Depends(get_db),
):

    validated_phone = validate_phone(phone)
    if not validated_phone:
        raise HTTPException(
            status_code=400,
            detail="Invalid phone number",
        )

    debt = db.query(Debt).filter(
        Debt.debt_id == debt_id,
        Debt.creditor_phone == validated_phone,
    ).first()

    if not debt:
        raise HTTPException(
            status_code=404,
            detail="Debt not found or does not belong to this trader.",
        )

    if debt.status == "settled":
        raise HTTPException(
            status_code=400,
            detail="Cannot send reminder — this debt is already settled.",
        )

    trader = db.query(Trader).filter(
        Trader.phone_number == validated_phone
    ).first()

    creditor_name = validated_phone  # fallback
    if trader:
        creditor_name = validated_phone  # extend this when you add trader names

    try:
        success = await send_debt_reminder(
            debtor_phone=debt.debtor_phone,
            creditor_name=creditor_name,
            amount_ngn=debt.amount_ngn,
            description=debt.description,
        )
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"SMS send failed: {e}",
        )

    if not success:
        raise HTTPException(
            status_code=503,
            detail="SMS send failed. Check Africa's Talking configuration.",
        )

    if debt.status == "pending":
        debt.status = "reminded"
        db.commit()

    print(f"📱 Reminder sent: {debt_id[:8]}... → {debt.debtor_phone}")

    return {
        "message": "Reminder sent successfully.",
        "debt_id": debt.debt_id,
        "debtor_phone": debt.debtor_phone,
        "amount_ngn": debt.amount_ngn,
        "status": debt.status,
    }