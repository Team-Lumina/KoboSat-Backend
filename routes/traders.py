from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional
from services.nostr_service import generate_keypair  # ← ADD THIS BACK

from db.database import get_db
from models.trader import Trader
from utils.validators import validate_phone, validate_language
from utils.auth import get_current_user

router = APIRouter()

class RegisterRequest(BaseModel):
    phone_number: str
    language: str = "en"


class LanguageUpdateRequest(BaseModel):
    phone_number: str
    language: str

@router.post("/traders/register")
async def register_trader(
    req: RegisterRequest,
    db: Session = Depends(get_db),
):

    phone = validate_phone(req.phone_number)
    if not phone:
        raise HTTPException(
            status_code=400,
            detail="Invalid phone number. Use Nigerian format e.g. 08012345678",
        )

    language = validate_language(req.language)
    if not language:
        raise HTTPException(
            status_code=400,
            detail="Language must be one of: en, yo, ha, ig",
        )

    existing = db.query(Trader).filter(
        Trader.phone_number == phone
    ).first()

    if existing:
        return {
            "message": "Welcome back! Wallet already exists.",
            "phone_number": existing.phone_number,
            "language": existing.language,
            "nostr_pubkey": existing.nostr_pubkey,
            "is_new": False,
        }

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

    print(f"✅ New trader registered: {phone}")

    return {
        "message": "Wallet created successfully.",
        "phone_number": trader.phone_number,
        "language": trader.language,
        "nostr_pubkey": trader.nostr_pubkey,
        "is_new": True,
    }


@router.patch("/traders/language")
async def update_language(
    req: LanguageUpdateRequest,
    current_phone: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    phone = validate_phone(req.phone_number)
    if not phone:
        raise HTTPException(
            status_code=400,
            detail="Invalid phone number",
        )

    language = validate_language(req.language)
    if not language:
        raise HTTPException(
            status_code=400,
            detail="Language must be one of: en, yo, ha, ig",
        )

    trader = db.query(Trader).filter(
        Trader.phone_number == phone
    ).first()

    if not trader:
        raise HTTPException(
            status_code=404,
            detail="Trader not found. Please register first.",
        )

    trader.language = language
    db.commit()

    return {
        "message": "Language updated.",
        "phone_number": trader.phone_number,
        "language": trader.language,
    }


@router.get("/traders/{phone}")
async def get_trader(
    phone: str,
    current_phone: str = Depends(get_current_user),
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

    return {
        "phone_number": trader.phone_number,
        "language": trader.language,
        "nostr_pubkey": trader.nostr_pubkey,
        "balance_sats": trader.balance_sats,
        "created_at": trader.created_at.isoformat() if trader.created_at else None,
    }