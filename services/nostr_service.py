import os
import json
import time
import hashlib
import asyncio
import secrets

import websockets
from config import settings


def _get_signer():

    try:
        import coincurve
        return "coincurve", coincurve
    except ImportError:
        pass

    try:
        from cryptography.hazmat.primitives.asymmetric.ec import (
            SECP256K1, EllipticCurvePrivateKey
        )
        return "cryptography", None
    except ImportError:
        pass

    return "none", None


SIGNER, SIGNER_LIB = _get_signer()


def generate_keypair() -> dict:

    privkey_bytes = os.urandom(32)

    while int.from_bytes(privkey_bytes, 'big') == 0:
        privkey_bytes = os.urandom(32)

    privkey_hex = privkey_bytes.hex()

    if SIGNER == "coincurve":
        import coincurve
        privkey_obj = coincurve.PrivateKey(privkey_bytes)

        pubkey_bytes = privkey_obj.public_key.format(compressed=True)[1:]
        pubkey_hex = pubkey_bytes.hex()
    else:
        pubkey_hex = hashlib.sha256(privkey_bytes).hexdigest()

    return {
        "pubkey_hex": pubkey_hex,
        "privkey_hex": privkey_hex,
    }



def _schnorr_sign(privkey_bytes: bytes, msg_bytes: bytes) -> bytes:

    P = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F
    N = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
    G = (
        0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798,
        0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8,
    )

    def point_add(P1, P2):
        if P1 is None:
            return P2
        if P2 is None:
            return P1
        if P1[0] == P2[0] and P1[1] != P2[1]:
            return None
        if P1 == P2:
            lam = (3 * P1[0] * P1[0] * pow(2 * P1[1], P - 2, P)) % P
        else:
            lam = ((P2[1] - P1[1]) * pow(P2[0] - P1[0], P - 2, P)) % P
        x3 = (lam * lam - P1[0] - P2[0]) % P
        return (x3, (lam * (P1[0] - x3) - P1[1]) % P)

    def point_mul(P1, n):
        R = None
        for i in range(256):
            if (n >> i) & 1:
                R = point_add(R, P1)
            P1 = point_add(P1, P1)
        return R

    def bytes_from_int(x):
        return x.to_bytes(32, 'big')

    def int_from_bytes(b):
        return int.from_bytes(b, 'big')

    def tagged_hash(tag, msg):
        tag_hash = hashlib.sha256(tag.encode()).digest()
        return hashlib.sha256(tag_hash + tag_hash + msg).digest()

    d0 = int_from_bytes(privkey_bytes)
    if not (1 <= d0 <= N - 1):
        raise ValueError("Invalid private key")

    P1 = point_mul(G, d0)
    d = d0 if P1[1] % 2 == 0 else N - d0

    rand = tagged_hash("BIP0340/nonce", privkey_bytes + bytes_from_int(P1[0]) + msg_bytes)
    k0 = int_from_bytes(rand) % N
    if k0 == 0:
        raise ValueError("Bad nonce")

    R = point_mul(G, k0)
    k = k0 if R[1] % 2 == 0 else N - k0

    e = int_from_bytes(
        tagged_hash(
            "BIP0340/challenge",
            bytes_from_int(R[0]) + bytes_from_int(P1[0]) + msg_bytes,
        )
    ) % N

    sig = bytes_from_int(R[0]) + bytes_from_int((k + e * d) % N)
    return sig


def _build_event(privkey_hex: str, pubkey_hex: str, content: str) -> dict:

    timestamp = int(time.time())

    serialised = json.dumps(
        [0, pubkey_hex, timestamp, 1, [], content],
        separators=(",", ":"),
        ensure_ascii=False,
    )

    event_id = hashlib.sha256(serialised.encode("utf-8")).hexdigest()

    privkey_bytes = bytes.fromhex(privkey_hex)
    msg_bytes = bytes.fromhex(event_id)
    sig_bytes = _schnorr_sign(privkey_bytes, msg_bytes)
    sig_hex = sig_bytes.hex()

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
        return ""

    content = (
        f"⚡ KoboSats Payment Received\n"
        f"Amount: \u20a6{amount_ngn:,.0f} ({int(amount_sats):,} sats)\n"
        f"Ref: {invoice_hash[:16]}...\n"
        f"#KoboSats #Bitcoin #Nigeria"
    )

    try:
        event = _build_event(privkey_hex, pubkey_hex, content)
        return await _publish_to_all_relays(event)
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
        return ""

    content = (
        f"📋 KoboSats Debt Record\n"
        f"Amount: \u20a6{amount_ngn:,.0f}\n"
        f"For: {description}\n"
        f"#KoboSats #Nigeria"
    )

    try:
        event = _build_event(privkey_hex, pubkey_hex, content)
        return await _publish_to_all_relays(event)
    except Exception as e:
        print(f"⚠️  Nostr debt publish failed: {e}")
        return ""