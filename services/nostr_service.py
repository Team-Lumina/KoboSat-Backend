import os
import json
import time
import hashlib
import asyncio
import secrets

import coincurve
import websockets

from config import settings

def generate_keypair() -> dict:

    privkey_bytes = os.urandom(32)
    privkey_hex = privkey_bytes.hex()

    privkey_obj = coincurve.PrivateKey(privkey_bytes)

    pubkey_bytes = privkey_obj.public_key.format(compressed=True)[1:]
    pubkey_hex = pubkey_bytes.hex()

    return {
        "pubkey_hex": pubkey_hex,
        "privkey_hex": privkey_hex,
    }


def _build_event(privkey_hex: str, pubkey_hex: str, content: str) -> dict:

    timestamp = int(time.time())

    serialised = json.dumps(
        [0, pubkey_hex, timestamp, 1, [], content],
        separators=(",", ":"),
        ensure_ascii=False,
    )

    event_id = hashlib.sha256(serialised.encode("utf-8")).hexdigest()

    privkey_bytes = bytes.fromhex(privkey_hex)
    privkey_obj = coincurve.PrivateKey(privkey_bytes)

    sig_bytes = privkey_obj.sign_recoverable(
        bytes.fromhex(event_id),
        hasher=None,
    )

    sig_hex = sig_bytes[:64].hex()

    return {
        "id":         event_id,
        "pubkey":     pubkey_hex,
        "created_at": timestamp,
        "kind":       1,
        "tags":       [],
        "content":    content,
        "sig":        sig_hex,
    }


async def _publish_to_relay(relay_url: str, event: dict) -> bool:

    message = json.dumps(["EVENT", event])

    try:
        async with websockets.connect(
            relay_url,
            open_timeout=5,
            close_timeout=5,
        ) as ws:
            await ws.send(message)

            response_raw = await asyncio.wait_for(ws.recv(), timeout=5)
            response = json.loads(response_raw)

            if isinstance(response, list) and len(response) >= 3:
                accepted = response[2]
                relay_msg = response[3] if len(response) > 3 else ""
                if accepted:
                    print(f"   ✅ Relay accepted: {relay_url}")
                    return True
                else:
                    print(f"   ⚠️  Relay rejected ({relay_url}): {relay_msg}")
                    return False

            print(f"   ⚠️  Unexpected relay response: {response}")
            return False

    except asyncio.TimeoutError:
        print(f"   ⚠️  Relay timeout: {relay_url}")
        return False
    except Exception as e:
        print(f"   ⚠️  Relay error ({relay_url}): {e}")
        return False


async def _publish_to_all_relays(event: dict) -> str:

    relays = [r.strip() for r in settings.NOSTR_RELAYS.split(",")]

    print(f"📡 Publishing Nostr event to {len(relays)} relays...")

    results = await asyncio.gather(
        *[_publish_to_relay(relay, event) for relay in relays],
        return_exceptions=True,
    )

    accepted = sum(1 for r in results if r is True)
    print(f"   Published to {accepted}/{len(relays)} relays")

    return event["id"]

async def publish_payment_event(
    privkey_hex: str,
    pubkey_hex: str,
    amount_sats: float,
    amount_ngn: float,
    invoice_hash: str,
) -> str:

    if not privkey_hex or not pubkey_hex:
        print("⚠️  Trader has no Nostr keys — skipping publish")
        return ""

    content = (
        f"⚡ KoboSats Payment Received\n"
        f"Amount: \u20a6{amount_ngn:,.0f} ({int(amount_sats):,} sats)\n"
        f"Ref: {invoice_hash[:16]}...\n"
        f"Verified on Bitcoin Lightning + Nostr\n"
        f"#KoboSats #Bitcoin #Nigeria"
    )

    try:
        event = _build_event(privkey_hex, pubkey_hex, content)
        event_id = await _publish_to_all_relays(event)
        return event_id
    except Exception as e:
        print(f"⚠️  Nostr payment publish failed: {e}")
        return ""


async def publish_debt_event(
    privkey_hex: str,
    pubkey_hex: str,
    debt_id: str,
    debtor_phone: str,
    amount_ngn: float,
    description: str,
) -> str:

    if not privkey_hex or not pubkey_hex:
        print("⚠️  Trader has no Nostr keys — skipping publish")
        return ""

    content = (
        f"📋 KoboSats Debt Record\n"
        f"Amount: \u20a6{amount_ngn:,.0f}\n"
        f"For: {description}\n"
        f"Status: pending\n"
        f"ID: {debt_id[:8]}...\n"
        f"#KoboSats #Nigeria"
    )

    try:
        event = _build_event(privkey_hex, pubkey_hex, content)
        event_id = await _publish_to_all_relays(event)
        return event_id
    except Exception as e:
        print(f"⚠️  Nostr debt publish failed: {e}")
        return ""