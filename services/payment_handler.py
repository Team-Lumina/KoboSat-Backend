"""
services/payment_handler.py

Called automatically by BreezEventListener when a payment arrives.
This is the chain reaction:
    Breez detects payment
        → update DB status to paid
        → publish Nostr event
        → send SMS to trader
"""
from datetime import datetime
from db.database import SessionLocal
from models.transaction import Transaction
from models.trader import Trader


async def handle_payment_received(invoice_hash: str, amount_sats: float):
    """
    Main handler called when a Lightning payment is received.

    Args:
        invoice_hash: the payment hash that identifies which invoice was paid
        amount_sats:  how many satoshis were received
    """
    db = SessionLocal()

    try:
        # ── Step 1: Find the transaction in DB ────────────────────────────────
        tx = db.query(Transaction).filter(
            Transaction.breez_invoice_hash == invoice_hash
        ).first()

        if not tx:
            print(f"⚠️  No transaction found for hash {invoice_hash[:16]}...")
            return

        if tx.status == "paid":
            print(f"⚠️  Transaction {tx.id} already marked paid, skipping")
            return

        # ── Step 2: Mark as paid ──────────────────────────────────────────────
        tx.status = "paid"
        tx.paid_at = datetime.utcnow()
        db.commit()
        db.refresh(tx)
        print(f"✅ Transaction {tx.id} marked as paid — {amount_sats} sats")

        # ── Step 3: Get the trader ────────────────────────────────────────────
        trader = db.query(Trader).filter(
            Trader.phone_number == tx.trader_phone
        ).first()

        if not trader:
            print(f"⚠️  Trader not found for phone {tx.trader_phone}")
            return

        # ── Step 4: Update cached balance ─────────────────────────────────────
        trader.balance_sats = (trader.balance_sats or 0) + amount_sats
        db.commit()

        # ── Step 5: Publish to Nostr ──────────────────────────────────────────
        try:
            from services.nostr_service import publish_payment_event
            event_id = await publish_payment_event(
                privkey_hex=trader.nostr_privkey,
                pubkey_hex=trader.nostr_pubkey,
                amount_sats=amount_sats,
                amount_ngn=tx.amount_ngn,
                invoice_hash=invoice_hash,
            )
            tx.nostr_event_id = event_id
            db.commit()
            print(f"📡 Nostr event published: {event_id[:16]}...")
        except Exception as e:
            # Nostr failure should NOT stop the payment from being recorded
            print(f"⚠️  Nostr publish failed (payment still recorded): {e}")

        # ── Step 6: Send SMS confirmation ─────────────────────────────────────
        try:
            from services.sms import send_sms
            await send_sms(
                phone=trader.phone_number,
                message=(
                    f"KoboSats: Payment received!\n"
                    f"Amount: \u20a6{tx.amount_ngn:,.0f} ({int(amount_sats):,} sats)\n"
                    f"Your wallet has been updated."
                ),
            )
            print(f"📱 SMS sent to {trader.phone_number}")
        except Exception as e:
            # SMS failure should NOT stop the payment from being recorded
            print(f"⚠️  SMS failed (payment still recorded): {e}")

    except Exception as e:
        print(f"❌ Payment handler critical error: {e}")
        db.rollback()

    finally:
        db.close()