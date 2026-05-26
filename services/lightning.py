import logging
from services.breez import get_sdk
import breez_sdk_spark as breez

logger = logging.getLogger(__name__)


async def create_lightning_invoice(
    amount_sats: int,
    description: str,
    phone_number: str
) -> dict:
    """
    Creates a Lightning invoice for the trader to receive payment.
    Returns the invoice string and amount.
    """
    try:
        sdk = await get_sdk()

        # Receive via Lightning invoice
        receive_request = breez.ReceiveLightningPaymentRequest(
            amount_msats=amount_sats * 1000,  # Breez uses millisatoshis
            description=description
        )

        response = await sdk.receive_lightning_payment(request=receive_request)

        return {
            "success": True,
            "invoice": response.invoice,
            "amount_sats": amount_sats,
            "description": description
        }

    except Exception as error:
        logger.error(f"Invoice creation error: {error}")
        raise


async def get_wallet_balance() -> dict:
    """
    Returns the current wallet balance from Breez SDK.
    """
    try:
        sdk = await get_sdk()
        info = await sdk.get_info()

        balance_sats = info.wallet_info.balance_sat

        return {
            "success": True,
            "balance_sats": balance_sats
        }

    except Exception as error:
        logger.error(f"Balance fetch error: {error}")
        raise


async def send_lightning_payment(bolt11: str) -> dict:
    """
    Sends a Lightning payment. Used for withdrawals.
    """
    try:
        sdk = await get_sdk()

        response = await sdk.send_lightning_payment(
            request=breez.SendLightningPaymentRequest(invoice=bolt11)
        )

        return {
            "success": True,
            "payment_id": response.payment.id if response.payment else None
        }

    except Exception as error:
        logger.error(f"Payment send error: {error}")
        raise