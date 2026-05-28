"""
services/lightning.py — Create invoices and fetch balance.
Uses the Breez Spark SDK (breez_sdk_spark v0.15.0).
"""
from services.breez import breez_service, BREEZ_AVAILABLE

if BREEZ_AVAILABLE:
    import breez_sdk_spark


async def create_invoice(amount_sats: int, description: str) -> dict:
    """
    Create a Lightning invoice for amount_sats satoshis.

    Returns:
        { "invoice": "lnbc...", "payment_hash": "abc123..." }
    """
    sdk = breez_service.get_sdk()

    if not sdk or not BREEZ_AVAILABLE:
        raise RuntimeError(
            "Breez Spark SDK is not connected. "
            "Check BREEZ_API_KEY and BREEZ_MNEMONIC in .env"
        )

    try:
        # Spark SDK receive payment request
        request = breez_sdk_spark.ReceivePaymentRequest(
            amount=breez_sdk_spark.Amount(
                sat=amount_sats,
            ),
            description=description,
        )

        response = await sdk.receive_payment(request)

        # Extract invoice from response
        invoice = ""
        payment_hash = ""

        if hasattr(response, 'invoice'):
            invoice = response.invoice
        if hasattr(response, 'payment_hash'):
            payment_hash = response.payment_hash

        # Some versions nest it differently
        if not invoice and hasattr(response, 'destination'):
            invoice = response.destination

        return {
            "invoice": invoice,
            "payment_hash": payment_hash,
        }

    except Exception as e:
        raise RuntimeError(f"Failed to create invoice: {e}")


async def get_balance() -> dict:
    """
    Fetch current wallet balance from Spark SDK.

    Returns:
        { "balance_sats": 47820, "pending_sats": 0 }
    """
    sdk = breez_service.get_sdk()

    if not sdk or not BREEZ_AVAILABLE:
        raise RuntimeError("Breez Spark SDK is not connected.")

    try:
        info = await sdk.get_info(
            breez_sdk_spark.GetInfoRequest(ensure_synced=True)
        )

        balance_sats = 0
        pending_sats = 0

        if hasattr(info, 'balance_sat'):
            balance_sats = info.balance_sat
        elif hasattr(info, 'wallet_info') and hasattr(info.wallet_info, 'balance_sat'):
            balance_sats = info.wallet_info.balance_sat

        if hasattr(info, 'pending_receive_sat'):
            pending_sats = info.pending_receive_sat

        return {
            "balance_sats": balance_sats,
            "pending_sats": pending_sats,
        }

    except Exception as e:
        raise RuntimeError(f"Failed to fetch balance: {e}")


async def list_payments(limit: int = 20) -> list:
    """
    Fetch recent received payments from Spark SDK.
    """
    sdk = breez_service.get_sdk()

    if not sdk or not BREEZ_AVAILABLE:
        return []

    try:
        request = breez_sdk_spark.ListPaymentsRequest(
            limit=limit,
        )
        response = await sdk.list_payments(request)

        payments = response.payments if hasattr(response, 'payments') else []

        return [
            {
                "payment_hash": p.id if hasattr(p, 'id') else "",
                "amount_sats": p.amount_sat if hasattr(p, 'amount_sat') else 0,
                "description": p.description if hasattr(p, 'description') else "",
                "status": str(p.status) if hasattr(p, 'status') else "",
                "timestamp": p.timestamp if hasattr(p, 'timestamp') else 0,
            }
            for p in payments
        ]

    except Exception as e:
        print(f"⚠️  Could not list payments: {e}")
        return []