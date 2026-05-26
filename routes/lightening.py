from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from db.database import get_db
from models.trader import Trader
from models.transaction import Transaction
from services.lightning import create_lightning_invoice, get_wallet_balance
from services.coingecko import get_btc_ngn_rate
from services.conversion import ngn_to_sats, sats_to_ngn
from pydantic import BaseModel

router = APIRouter()

class InvoiceRequest(BaseModel):
    phone_number: str
    amount_ngn: float

@router.post("/lightning/invoice")
async def generate_invoice(
    request: InvoiceRequest,
    db: Session = Depends(get_db)
):
    trader = db.query(Trader).filter(
        Trader.phone_number == request.phone_number
    ).first()

    if not trader:
        raise HTTPException(status_code=404, detail="Trader not found")

    try:
        rate = await get_btc_ngn_rate()
        amount_sats = ngn_to_sats(request.amount_ngn, rate)

        invoice_data = await create_lightning_invoice(
            amount_sats=amount_sats,
            description=f"KoboSats - N{request.amount_ngn} from {request.phone_number}",
            phone_number=request.phone_number
        )

        # Save pending transaction
        transaction = Transaction(
            trader_phone=request.phone_number,
            amount_sats=amount_sats,
            amount_ngn=request.amount_ngn,
            btc_ngn_rate=rate,
            status="pending"
        )
        db.add(transaction)
        db.commit()

        return {
            "success": True,
            "invoice": invoice_data.get("invoice"),
            "amount_sats": amount_sats,
            "amount_ngn": request.amount_ngn,
            "btc_ngn_rate": rate
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/lightning/balance/{phone_number}")
async def get_balance(phone_number: str, db: Session = Depends(get_db)):
    trader = db.query(Trader).filter(
        Trader.phone_number == phone_number
    ).first()

    if not trader:
        raise HTTPException(status_code=404, detail="Trader not found")

    try:
        rate = await get_btc_ngn_rate()
        balance_data = await get_wallet_balance()
        balance_sats = balance_data.get("balance_sats", 0)
        balance_ngn = sats_to_ngn(balance_sats, rate)

        return {
            "success": True,
            "balance_sats": balance_sats,
            "balance_ngn": balance_ngn,
            "btc_ngn_rate": rate
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))