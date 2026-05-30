
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
    

async def prepare_send(invoice: str) -> dict:

    sdk = breez_service.get_sdk()

    if not sdk or not BREEZ_AVAILABLE:
        raise RuntimeError("Breez Spark SDK is not connected.")

    try:

        prepare_req = breez_sdk_spark.PrepareSendPaymentRequest(
            payment_request=invoice,
        )

        prepare_response = await sdk.prepare_send_payment(prepare_req)

        print(f"   Prepare response fields: {[x for x in dir(prepare_response) if not x.startswith('_')]}")
        print(f"   Prepare response: {prepare_response}")

        amount_sats = 0
        fee_sats = 0
        description = ""

        if hasattr(prepare_response, 'amount_sat'):
            amount_sats = prepare_response.amount_sat
        elif hasattr(prepare_response, 'amount_sats'):
            amount_sats = prepare_response.amount_sats

        if hasattr(prepare_response, 'fee_sat'):
            fee_sats = prepare_response.fee_sat
        elif hasattr(prepare_response, 'fee_sats'):
            fee_sats = prepare_response.fee_sats

        if hasattr(prepare_response, 'description'):
            description = prepare_response.description or ""

        return {
            "amount_sats": amount_sats,
            "fee_sats": fee_sats,
            "description": description,
            "prepare_response": prepare_response,
        }

    except Exception as e:
        raise RuntimeError(f"Failed to prepare payment: {e}")


async def execute_send(prepare_response) -> dict:

    sdk = breez_service.get_sdk()

    if not sdk or not BREEZ_AVAILABLE:
        raise RuntimeError("Breez Spark SDK is not connected.")

    try:
        send_req = breez_sdk_spark.SendPaymentRequest(
            prepare_response=prepare_response,
        )

        response = await sdk.send_payment(send_req)

        print(f"   Send response fields: {[x for x in dir(response) if not x.startswith('_')]}")
        print(f"   Send response: {response}")

        payment_hash = ""
        fee_sats = 0

        if hasattr(response, 'payment'):
            p = response.payment
            if hasattr(p, 'id'):
                payment_hash = p.id
            if hasattr(p, 'fee_sat'):
                fee_sats = p.fee_sat

        return {
            "payment_hash": payment_hash,
            "fee_sats": fee_sats,
        }

    except Exception as e:
        raise RuntimeError(f"Payment failed: {e}")