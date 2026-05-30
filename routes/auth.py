from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db.database import get_db
from models.trader import Trader
from services.sms import generate_otp, verify_otp, send_sms
from services.nostr_service import generate_keypair
from utils.validators import validate_phone, validate_language
from utils.auth import create_access_token

router = APIRouter(prefix="/auth", tags=["Auth"])


class SendOTPRequest(BaseModel):
    phone_number: str


class VerifyOTPRequest(BaseModel):
    phone_number: str
    code: str
    language: str = "en"
    name: str | None = None


@router.post("/send-otp")
async def send_otp(req: SendOTPRequest, db: Session = Depends(get_db)):
    phone = validate_phone(req.phone_number)
    if not phone:
        raise HTTPException(
            status_code=400,
            detail="Invalid phone number. Use Nigerian format e.g. 08012345678",
        )

    code = generate_otp(phone)

    sms_sent = await send_sms(
        phone,
        f"Your KoboSats verification code is: {code}\n"
        f"Valid for 5 minutes. Do not share this code."
    )

    return {
        "message": "OTP sent successfully",
        "phone_number": phone,

        # Only expose in dev so frontend can display it — REMOVE in production
        "dev_code": code if not sms_sent else None,
    }


@router.post("/verify-otp")
async def verify_otp_and_login(
    req: VerifyOTPRequest,
    db: Session = Depends(get_db),
):
    phone = validate_phone(req.phone_number)
    if not phone:
        raise HTTPException(status_code=400, detail="Invalid phone number")

    if not verify_otp(phone, req.code):
        raise HTTPException(
            status_code=400,
            detail="Invalid or expired verification code",
        )

    trader = db.query(Trader).filter(Trader.phone_number == phone).first()
    is_new = False

    if not trader:
        language = validate_language(req.language) or "en"
        keypair = generate_keypair()
        trader = Trader(
            phone_number=phone,
            language=language,
            nostr_pubkey=keypair["pubkey_hex"],
            nostr_privkey=keypair["privkey_hex"],
            balance_sats=0.0,
        )
        db.add(trader)
        db.commit()
        db.refresh(trader)
        is_new = True
        print(f"✅ New trader registered via OTP: {phone}")

    token = create_access_token(phone)

    return {
        "message": "Welcome to KoboSats!" if is_new else "Welcome back!",
        "access_token": token,
        "token_type": "bearer",
        "is_new": is_new,
        "trader": {
            "phone_number": trader.phone_number,
            "language": trader.language,
            "nostr_pubkey": trader.nostr_pubkey,
            "balance_sats": trader.balance_sats,
        },
    }