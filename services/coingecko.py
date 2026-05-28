import time
import httpx
from config import settings

_cache = {
    "rate": None,
    "timestamp": 0,
}

CACHE_TTL = 60

FALLBACK_RATE = 150_000_000  # ₦150,000,000 per BTC


async def get_btc_ngn_rate() -> float:
    now = time.time()

    if _cache["rate"] and (now - _cache["timestamp"]) < CACHE_TTL:
        return _cache["rate"]

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(
                f"{settings.COINGECKO_BASE_URL}/simple/price",
                params={
                    "ids": "bitcoin",
                    "vs_currencies": "ngn",
                },
            )
            response.raise_for_status()
            data = response.json()

            rate = float(data["bitcoin"]["ngn"])

            _cache["rate"] = rate
            _cache["timestamp"] = now

            print(f"💱 BTC/NGN rate updated: ₦{rate:,.0f}")
            return rate

    except httpx.TimeoutException:
        print("⚠️  CoinGecko timeout — using cached/fallback rate")
    except httpx.HTTPStatusError as e:
        print(f"⚠️  CoinGecko HTTP error {e.response.status_code} — using cached/fallback rate")
    except Exception as e:
        print(f"⚠️  CoinGecko fetch failed: {e} — using cached/fallback rate")

    if _cache["rate"]:
        print(f"   Using stale cached rate: ₦{_cache['rate']:,.0f}")
        return _cache["rate"]

    print(f"   Using hardcoded fallback rate: ₦{FALLBACK_RATE:,.0f}")
    return float(FALLBACK_RATE)