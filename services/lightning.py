
from services.breez import breez_service, BREEZ_AVAILABLE

if BREEZ_AVAILABLE:
    import breez_sdk_spark


async def create_invoice(amount_sats: int, description: str) -> dict:

    sdk = breez_service.get_sdk()

    if not sdk or not BREEZ_AVAILABLE:
        raise RuntimeError(
            "Breez Spark SDK is not connected. "
            "Check BREEZ_API_KEY and BREEZ_MNEMONIC in .env"
        )

    try:
        payment_method = breez_sdk_spark.ReceivePaymentMethod.BOLT11_INVOICE(
            description=description,
            amount_sats=amount_sats,
            expiry_secs=3600,   # invoice expires in 1 hour
            payment_hash=None,
        )

        request = breez_sdk_spark.ReceivePaymentRequest(
            payment_method=payment_method,
        )

        response = await sdk.receive_payment(request)

        invoice = ""
        payment_hash = ""

        if hasattr(response, 'payment_request'):
            invoice = response.payment_request

        payment_hash = invoice[:64] if invoice else ""

        print(f"   Invoice: {invoice[:40]}..." if invoice else "   ⚠️  No invoice in response")

        return {
            "invoice": invoice,
            "payment_hash": payment_hash,
        }

    except Exception as e:
        raise RuntimeError(f"Failed to create invoice: {e}")

async def get_balance() -> dict:

    sdk = breez_service.get_sdk()

    if not sdk or not BREEZ_AVAILABLE:
        raise RuntimeError("Breez Spark SDK is not connected.")

    try:
        info = await sdk.get_info(
            breez_sdk_spark.GetInfoRequest(ensure_synced=True)
        )

        print(f"   Info fields: {[x for x in dir(info) if not x.startswith('_')]}")

        balance_sats = 0
        pending_sats = 0

        if hasattr(info, 'balance_sats'):
            balance_sats = info.balance_sats

        if hasattr(info, 'pending_receive_sat'):
            pending_sats = info.pending_receive_sat
        elif hasattr(info, 'pending_receive_sats'):
            pending_sats = info.pending_receive_sats

        return {
            "balance_sats": balance_sats,
            "pending_sats": pending_sats,
        }

    except Exception as e:
        raise RuntimeError(f"Failed to fetch balance: {e}")


async def list_payments(limit: int = 20) -> list:

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

            }
            for p in payments
        ]

    except Exception as e:
        print(f"⚠️  Could not list payments: {e}")
        return []