"""
routes/ussd.py — USSD session handler.

POST /api/v1/ussd          ← Africa's Talking gateway calls this
POST /api/v1/ussd/simulate ← USSDDemo.jsx calls this

How the text field works:
    text = ""        → first dial, show main menu
    text = "1"       → user chose option 1
    text = "1*2500"  → user chose option 1, then typed 2500
    text = "3*0803*5000*Rice" → option 3, phone, amount, description

We split text by "*" to get each input level.
Level 0 = first choice, level 1 = second input, etc.
"""
from fastapi import APIRouter, Form, Depends, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db.database import get_db
from models.trader import Trader
from models.debt import Debt
from models.transaction import Transaction
from services.nostr_service import generate_keypair
from services.coingecko import get_btc_ngn_rate
from services.conversion import ngn_to_sats, sats_to_ngn
from services.lightning import create_invoice, get_balance
from services.sms import send_sms
from locales import get_locale
from utils.validators import validate_phone

router = APIRouter()

async def process_ussd(
    phone_number: str,
    text: str,
    db: Session,
) -> tuple[str, str]:

    phone = validate_phone(phone_number) or phone_number

    # Split text into input levels
    # text=""     → inputs=[""]
    # text="1"    → inputs=["1"]
    # text="1*2500" → inputs=["1", "2500"]
    inputs = text.split("*") if text else [""]

    trader = db.query(Trader).filter(
        Trader.phone_number == phone
    ).first()

    if not trader:
        keypair = generate_keypair()
        trader = Trader(
            phone_number=phone,
            language="en",
            nostr_pubkey=keypair["pubkey_hex"],
            nostr_privkey=keypair["privkey_hex"],
            balance_sats=0.0,
        )
        db.add(trader)
        db.commit()
        db.refresh(trader)
        print(f"✅ Auto-registered USSD trader: {phone}")

    locale = get_locale(trader.language)

    level_0 = inputs[0] if inputs else ""

    if not level_0:
        return "CON", locale.MAIN_MENU

    if level_0 == "0":
        return "END", locale.GOODBYE

    if level_0 == "1":
        # Step 1: Ask for amount
        if len(inputs) == 1:
            return "CON", locale.ENTER_AMOUNT

        # Step 2: Process amount and create invoice
        amount_raw = inputs[1].strip()
        try:
            amount_ngn = float(amount_raw.replace(",", ""))
            if amount_ngn <= 0:
                raise ValueError
        except ValueError:
            return "END", locale.INVALID_AMOUNT

        try:
            rate = await get_btc_ngn_rate()
            amount_sats = ngn_to_sats(amount_ngn, rate)

            invoice_data = await create_invoice(
                amount_sats,
                f"KoboSats USSD N{amount_ngn:,.0f}",
            )

            # Save pending transaction
            tx = Transaction(
                trader_phone=phone,
                amount_sats=float(amount_sats),
                amount_ngn=amount_ngn,
                btc_ngn_rate=rate,
                breez_invoice_hash=invoice_data["payment_hash"],
                lightning_invoice=invoice_data["invoice"],
                status="pending",
            )
            db.add(tx)
            db.commit()

            # Send invoice to trader by SMS
            invoice_preview = invoice_data["invoice"][:30] + "..."
            await send_sms(
                phone,
                f"KoboSats Invoice:\n{invoice_data['invoice']}\n"
                f"Amount: N{amount_ngn:,.0f} ({amount_sats:,} sats)",
            )

            return "END", locale.INVOICE_CREATED.format(
                amount_ngn=int(amount_ngn),
                amount_sats=amount_sats,
            )

        except RuntimeError as e:
            print(f"⚠️  USSD invoice error: {e}")
            return "END", locale.ERROR_GENERIC

    #Option 2: Check Balance
    if level_0 == "2":
        try:
            balance_data = await get_balance()
            rate = await get_btc_ngn_rate()

            balance_sats = balance_data["balance_sats"]
            balance_ngn = sats_to_ngn(balance_sats, rate)

            # Update cached balance
            trader.balance_sats = float(balance_sats)
            db.commit()

            return "END", locale.BALANCE.format(
                sats=f"{balance_sats:,}",
                ngn=f"{int(balance_ngn):,}",
            )

        except RuntimeError as e:
            print(f"⚠️  USSD balance error: {e}")
            return "END", locale.ERROR_GENERIC

    #Option 3: Log Customer Debt
    if level_0 == "3":
        # Step 1: Ask for debtor phone
        if len(inputs) == 1:
            return "CON", locale.DEBT_ENTER_PHONE

        # Step 2: Ask for amount
        if len(inputs) == 2:
            return "CON", locale.DEBT_ENTER_AMOUNT

        # Step 3: Ask for description
        if len(inputs) == 3:
            return "CON", locale.DEBT_ENTER_DESC

        # Step 4: Save debt
        debtor_raw = inputs[1].strip()
        amount_raw = inputs[2].strip()
        description = inputs[3].strip()

        debtor_phone = validate_phone(debtor_raw) or debtor_raw

        try:
            amount_ngn = float(amount_raw.replace(",", ""))
            if amount_ngn <= 0:
                raise ValueError
        except ValueError:
            return "END", locale.INVALID_AMOUNT

        # Save to DB
        debt = Debt(
            creditor_phone=phone,
            debtor_phone=debtor_phone,
            amount_ngn=amount_ngn,
            description=description,
            status="pending",
        )
        db.add(debt)
        db.commit()

        print(f"📋 USSD debt logged: {phone} ← {debtor_phone} N{amount_ngn:,.0f}")

        # Publish to Nostr in background
        try:
            from services.nostr_service import publish_debt_event
            await publish_debt_event(
                privkey_hex=trader.nostr_privkey,
                pubkey_hex=trader.nostr_pubkey,
                debt_id=debt.debt_id,
                debtor_phone=debtor_phone,
                amount_ngn=amount_ngn,
                description=description,
            )
        except Exception as e:
            print(f"⚠️  Nostr publish failed: {e}")

        return "END", locale.DEBT_LOGGED.format(
            debtor=debtor_phone[-4:],
            amount_ngn=int(amount_ngn),
        )

    #Option 4: View My Debts
    if level_0 == "4":
        debts = (
            db.query(Debt)
            .filter(
                Debt.creditor_phone == phone,
                Debt.status.in_(["pending", "reminded"]),
            )
            .order_by(Debt.created_at.desc())
            .limit(4)
            .all()
        )

        if not debts:
            return "END", locale.NO_DEBTS

        total = sum(d.amount_ngn for d in debts)
        message = locale.DEBTS_LIST_HEADER.format(total=f"{int(total):,}")

        for i, debt in enumerate(debts, 1):
            message += locale.DEBT_ITEM.format(
                index=i,
                phone=debt.debtor_phone[-4:],
                amount=f"{int(debt.amount_ngn):,}",
            )

        return "END", message.strip()

    #Option 5: Change Language
    if level_0 == "5":
        # Step 1: Show language options
        if len(inputs) == 1:
            return "CON", locale.CHOOSE_LANGUAGE

        # Step 2: Save language choice
        choice = inputs[1].strip()
        lang_map = {
            "1": "en",
            "2": "yo",
            "3": "ha",
            "4": "ig",
        }
        new_lang = lang_map.get(choice)

        if not new_lang:
            return "END", locale.INVALID_CHOICE

        trader.language = new_lang
        db.commit()

        new_locale = get_locale(new_lang)
        return "END", new_locale.LANGUAGE_UPDATED

    return "END", locale.INVALID_CHOICE


#Africa's Talking Real Endpoint

@router.post("/ussd", response_class=PlainTextResponse)
async def handle_ussd(
    sessionId: str = Form(...),
    serviceCode: str = Form(...),
    phoneNumber: str = Form(...),
    text: str = Form(default=""),
    db: Session = Depends(get_db),
):
    response_type, message = await process_ussd(phoneNumber, text, db)
    return f"{response_type} {message}"


# Web Emulator Endpoint

class SimulateRequest(BaseModel):
    phone_number: str
    text: str = ""


@router.post("/ussd/simulate")
async def simulate_ussd(
    req: SimulateRequest,
    db: Session = Depends(get_db),
):
    response_type, message = await process_ussd(
        req.phone_number,
        req.text,
        db,
    )

    return {
        "type": response_type,
        "message": message,
        "session_text": req.text,
        "continue": response_type == "CON",
    }