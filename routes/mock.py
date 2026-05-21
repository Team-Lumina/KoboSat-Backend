from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

class InvoiceRequest(BaseModel):
    amount_ngn: float

class USSDRequest(BaseModel):
    text_input: str


@router.get("/balance")
def get_balance():
    return {
        "sats_balance": 45000,
        "ngn_equivalent": 2500
    }

@router.post("/invoice")
def create_invoice(request: InvoiceRequest):
    return {
        "invoice_string": "lnbc50k1p3xyzabcdefghijklmnopqrstuvwxyz0123456789",
        "sats_amount": 90000
    }

@router.get("/transactions")
def get_transactions():
    return [
        {
            "id": 1,
            "type": "receive",
            "amount_ngn": 1500,
            "date": "2026-05-20T14:30:00Z",
            "nostr_link": "nostr:nevent1qqsxyz123abc"
        },
        {
            "id": 2,
            "type": "receive",
            "amount_ngn": 3000,
            "date": "2026-05-19T10:15:00Z",
            "nostr_link": "nostr:nevent1qqsdef456ghi"
        },
    ]

@router.get("/debts")
def get_debts():
    return [
        {
            "debt_id": "101",
            "customer_phone": "08012345678",
            "amount_ngn": 3000,
            "status": "pending",
            "due_date": "2026-05-25"
        },
        {
            "debt_id": "102",
            "customer_phone": "08098765432",
            "amount_ngn": 1500,
            "status": "pending",
            "due_date": "2026-05-28"
        },
    ]

@router.post("/debts/log")
def log_debt(body: dict):
    return {
        "success": True,
        "debt_id": "104",
        "message": "Debt logged successfully"
    }

@router.patch("/debts/{debt_id}/settle")
def settle_debt(debt_id: str):
    return {
        "success": True,
        "message": f"Debt {debt_id} marked as settled"
    }

@router.post("/debts/{debt_id}/remind")
def send_reminder(debt_id: str):
    return {
        "success": True,
        "message": f"Reminder sent for debt {debt_id}"
    }

@router.post("/ussd/simulate")
def ussd_simulate(request: USSDRequest):
    text = request.text_input.strip()


    if text in ["", "*945*BTC#", "*945#", "0"]:
        return {
            "screen_text": (
                "KoboSats\n"
                "─────────────\n"
                "1. Receive\n"
                "2. Balance\n"
                "3. Log Debt\n"
                "4. View Debts"
            )
        }

    if text == "1":
        return {"screen_text": "Enter amount\nin Naira:\n\n[  ____  ]"}

    if text == "2":
        return {
            "screen_text": (
                "Your Balance\n"
                "─────────────\n"
                "45,000 sats\n"
                "≈ N2,500"
            )
        }

    if text == "3":
        return {"screen_text": "Enter customer\nphone number:\n\n[  ____  ]"}

    if text == "4":
        return {
            "screen_text": (
                "Outstanding:\n"
                "─────────────\n"
                "1. N3,000 - 0801\n"
                "2. N1,500 - 0809\n"
                "─────────────\n"
                "Total: N4,500"
            )
        }


    if text.isdigit() and len(text) >= 3:
        return {
            "screen_text": (
                f"Invoice created!\n"
                f"─────────────\n"
                f"Amount: N{text}\n"
                f"Sats: {int(int(text) * 3.6)}\n"
                f"─────────────\n"
                f"Customer SMS\n"
                f"sent. Waiting..."
            )
        }

    return {
        "screen_text": (
            "Invalid input.\n"
            "─────────────\n"
            "Press 0 for\n"
            "main menu"
        )
    }