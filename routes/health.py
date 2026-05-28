
from fastapi import APIRouter
from services.breez import breez_service, BREEZ_AVAILABLE
from services.sms import AT_AVAILABLE

router = APIRouter()

@router.get("/health")
async def health_check():
    try:
        from db.database import SessionLocal
        from sqlalchemy import text
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)[:50]}"

    if not BREEZ_AVAILABLE:
        breez_status = "sdk not installed"
    elif breez_service.is_connected:
        breez_status = "connected"
    else:
        breez_status = "not connected — check BREEZ_API_KEY in .env"

    sms_status = "connected" if AT_AVAILABLE else "not connected — check AT_API_KEY in .env"

    try:
        import httpx
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(
                "https://api.coingecko.com/api/v3/ping"
            )
            coingecko_status = "reachable" if resp.status_code == 200 else f"error {resp.status_code}"
    except Exception:
        coingecko_status = "unreachable — will use cached rate"

    return {
        "status": "ok",
        "app": "KoboSats",
        "version": "1.0.0",
        "message": "Bitcoin Lightning payments for Nigerian market traders",
        "services": {
            "database":  db_status,
            "breez":     breez_status,
            "sms":       sms_status,
            "coingecko": coingecko_status,
        },
    }
