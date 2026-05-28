from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from db.database import get_db
from models.trader import Trader
from models.transaction import Transaction
from services.lightning import (
    create_invoice,
    get_balance as fetch_balance,
    list_payments,
)
from services.coingecko import get_btc_ngn_rate
from services.conversion import ngn_to_sats, sats_to_ngn
from utils.validators import validate_phone, validate_amount

router = APIRouter()

class InvoiceRequest(BaseModel):
    phone_number: str
    amount_ngn: float

@router.post("/lightning/invoice")
async def generate_invoice(
    req: InvoiceRequest,
    db: Session = Depends(get_db)
):
    
    phone = validate_phone(req.phone_number)
    if not phone:
        raise HTTPException(
            status_code=400,
            detail="Invalid phone number. Use Nigerian format e.g. 08012345678",
        )

    amount = validate_amount(req.amount_ngn)
    if not amount:
        raise HTTPException(
            status_code=400,
            detail="Invalid amount. Must be between ₦1 and ₦10,000,000",
        )

    trader = db.query(Trader).filter(
        Trader.phone_number == phone
    ).first()

    if not trader:
        raise HTTPException(
            status_code=404,
            detail="Trader not found. Please register first.")

    try:
        rate = await get_btc_ngn_rate()
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Could not fetch exchange rate: {e}"
        )

    try:
        amount_sats = ngn_to_sats(amount, rate)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if amount_sats < 1:
        raise HTTPException(
            status_code=400,
            detail="Amount too small. Minimum is 1 satoshi.",)

    description = f"KoboSats payment \u20a6{amount:,.0f}"

    try:
        invoice_data = await create_invoice(amount_sats, description)
    except RuntimeError as e:
        raise HTTPException(
            status_code=503,
            detail=str(e)
        )

    tx = Transaction(
        trader_phone=phone,
        amount_sats=float(amount_sats),
        amount_ngn=amount,
        btc_ngn_rate=rate,
        breez_invoice_hash=invoice_data["payment_hash"],
        lightning_invoice=invoice_data["invoice"],
        status="pending",
    )
    db.add(tx)
    db.commit()
    db.refresh(tx)

    print(f"⚡ Invoice created for {phone}: {amount_sats} sats (₦{amount:,.0f})")

    return {
        "invoice": invoice_data["invoice"],
        "payment_hash": invoice_data["payment_hash"],
        "amount_sats": amount_sats,
        "amount_ngn": amount,
        "btc_ngn_rate": rate,
        "transaction_id": tx.id,
        "status": "pending",
    }

@router.get("/lightning/balance/{phone}")
async def get_balance(
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

    try:
        balance_data = await fetch_balance()
    except RuntimeError as e:
        raise HTTPException(
            status_code=503,
            detail=str(e),
        )

    try:
        rate = await get_btc_ngn_rate()
    except Exception:
        rate = 150_000_000  # fallback

    balance_sats = balance_data["balance_sats"]
    pending_sats = balance_data["pending_sats"]
    balance_ngn = sats_to_ngn(balance_sats, rate)

    trader.balance_sats = float(balance_sats)
    db.commit()

    return {
        "phone_number": validated_phone,
        "balance_sats": balance_sats,
        "balance_ngn": round(balance_ngn, 2),
        "pending_sats": pending_sats,
        "btc_ngn_rate": rate,
    }


@router.get("/transactions/{phone}")
async def get_transactions(
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

    transactions = (
        db.query(Transaction)
        .filter(
            Transaction.trader_phone == validated_phone,
            Transaction.status == "paid",
        )
        .order_by(Transaction.paid_at.desc())
        .limit(20)
        .all()
    )

    return {
        "phone_number": validated_phone,
        "count": len(transactions),
        "transactions": [
            {
                "id": tx.id,
                "amount_sats": int(tx.amount_sats),
                "amount_ngn": tx.amount_ngn,
                "btc_ngn_rate": tx.btc_ngn_rate,
                "status": tx.status,
                "nostr_event_id": tx.nostr_event_id,
                "nostr_link": (
                    f"https://njump.me/{tx.nostr_event_id}"
                    if tx.nostr_event_id else None
                ),
                "created_at": (
                    tx.created_at.isoformat()
                    if tx.created_at else None
                ),
                "paid_at": (
                    tx.paid_at.isoformat()
                    if tx.paid_at else None
                ),
            }
            for tx in transactions
        ],
    }


@router.get("/transactions/{phone}/{tx_id}")
async def get_single_transaction(
    phone: str,
    tx_id: int,
    db: Session = Depends(get_db),
):

    validated_phone = validate_phone(phone)
    if not validated_phone:
        raise HTTPException(
            status_code=400,
            detail="Invalid phone number",
        )

    tx = db.query(Transaction).filter(
        Transaction.id == tx_id,
        Transaction.trader_phone == validated_phone,
    ).first()

    if not tx:
        raise HTTPException(
            status_code=404,
            detail="Transaction not found.",
        )

    return {
        "id": tx.id,
        "amount_sats": int(tx.amount_sats),
        "amount_ngn": tx.amount_ngn,
        "status": tx.status,
        "nostr_event_id": tx.nostr_event_id,
        "nostr_link": (
            f"https://njump.me/{tx.nostr_event_id}"
            if tx.nostr_event_id else None
        ),
        "created_at": tx.created_at.isoformat() if tx.created_at else None,
        "paid_at": tx.paid_at.isoformat() if tx.paid_at else None,
    }