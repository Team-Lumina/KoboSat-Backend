import os
import asyncio
from random import seed
from config import settings

try:
    import breez_sdk_spark
    BREEZ_AVAILABLE = True
except ImportError:
    BREEZ_AVAILABLE = False
    print("⚠️  breez_sdk_spark not installed")


class BreezEventListener(breez_sdk_spark.EventListener if BREEZ_AVAILABLE else object):
    async def on_event(self, event):
        if not BREEZ_AVAILABLE:
            return

        print(f"⚡ Spark event: {type(event).__name__}")

        try:
            if isinstance(event, breez_sdk_spark.SdkEvent.PAYMENT_SUCCEEDED):
                details = event.details
                print(f"   Payment details fields: {[x for x in dir(details) if not x.startswith('_')]}")

                payment_hash =""
                amount_sats = 0

                if hasattr(details, 'id'):
                    payment_hash = details.id
                elif hasattr(details, 'payment_hash'):
                    payment_hash = details.payment_hash


                if hasattr(details, 'amount_sat'):
                    amount_sats = details.amount_sat
                elif hasattr(details, 'amount_sats'):
                    amount_sats = details.amount_sats
                elif hasattr(details, 'amount_msat'):
                    amount_sats = details.amount_msat / 1000

                print(f"💰 Payment received! hash={payment_hash[:16] if payment_hash else 'unknown'}... sats={amount_sats}")

                try:
                    from services.payment_handler import handle_payment_received
                    await handle_payment_received(payment_hash, amount_sats)
                except Exception as e:
                    print(f"⚠️  Payment handler error: {e}")

        except Exception as e:
            print(f"⚠️  Event processing error: {e}")


class BreezService:

    def __init__(self):
        self.sdk = None
        self._connected = False

    async def connect(self):
        if not BREEZ_AVAILABLE:
            print("⚠️  breez_sdk_spark not installed — Lightning disabled")
            return

        if not settings.BREEZ_API_KEY:
            print("⚠️  BREEZ_API_KEY not set in .env — Lightning disabled")
            return

        if not settings.BREEZ_MNEMONIC:
            print("⚠️  BREEZ_MNEMONIC not set in .env — Lightning disabled")
            return

        try:
            os.makedirs(settings.BREEZ_STORAGE_DIR, exist_ok=True)

            config = breez_sdk_spark.default_config(
                network=breez_sdk_spark.Network.MAINNET,
            )

            config.api_key = settings.BREEZ_API_KEY

            seed = breez_sdk_spark.Seed.MNEMONIC(
                mnemonic=settings.BREEZ_MNEMONIC,
                passphrase=None,
            )

            request = breez_sdk_spark.ConnectRequest(
                config=config,
                seed=seed,
                storage_dir=settings.BREEZ_STORAGE_DIR,
            )

            self.sdk = await breez_sdk_spark.connect(request)

            await self.sdk.add_event_listener(BreezEventListener())

            self._connected = True
            print("✅ Breez Spark SDK connected")

            try:
                info = await self.sdk.get_info(
                    breez_sdk_spark.GetInfoRequest(ensure_synced=False)
                )
                balance = info.balance_sat if hasattr(info, 'balance_sat') else 0
                print(f"   Balance: {balance:,} sats")
            except Exception as e:
                print(f"   (Could not fetch balance: {e})")

        except Exception as e:
            print(f"❌ Breez connection failed: {e}")
            self._connected = False

    async def disconnect(self):
        """Cleanly disconnect on shutdown."""
        if self.sdk and self._connected:
            try:
                await self.sdk.disconnect()
                self._connected = False
                print("✅ Breez Spark SDK disconnected")
            except Exception as e:
                print(f"⚠️  Breez disconnect error: {e}")

    def get_sdk(self):
        return self.sdk

    @property
    def is_connected(self):
        return self._connected


breez_service = BreezService()