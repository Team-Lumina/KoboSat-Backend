import httpx
from config import settings

AT_AVAILABLE = bool(settings.AT_API_KEY)

if AT_AVAILABLE:
    print("✅ Africa's Talking SMS ready")
else:
    print("⚠️  AT_API_KEY not set — SMS disabled")

def normalise_phone(phone: str) -> str:

    phone = phone.strip().replace(" ", "").replace("-", "").replace("(", "").replace(")", "")

    if phone.startswith("+234"):
        return phone

    if phone.startswith("234"):
        return f"+{phone}"

    if phone.startswith("0") and len(phone) == 11:
        return f"+234{phone[1:]}"

    if len(phone) == 10 and phone[0] in ("7", "8", "9"):
        return f"+234{phone}"

    return phone

async def send_sms(phone: str, message: str) -> bool:
    
    normalised = normalise_phone(phone)

    if not settings.AT_API_KEY:
        print(f"[SMS NOT SENT — no API key]")
        print(f"  To:      {normalised}")
        print(f"  Message: {message}")
        return False

    try:
        import httpx

        if settings.AT_USERNAME == "sandbox":
            url = "https://api.sandbox.africastalking.com/version1/messaging"
        else:
            url = "https://api.africastalking.com/version1/messaging"

        headers = {
            "apiKey": settings.AT_API_KEY,
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
        }

        data = {
            "username": settings.AT_USERNAME,
            "to": normalised,
            "message": message,
        }

        async with httpx.AsyncClient(timeout=10.0, verify=False) as client:
            response = await client.post(url, headers=headers, data=data)
            response.raise_for_status()
            result = response.json()

            recipients = (
                result
                .get("SMSMessageData", {})
                .get("Recipients", [])
            )

            if recipients and recipients[0].get("status") == "Success":
                print(f"📱 SMS sent to {normalised}")
                return True
            else:
                print(f"⚠️  SMS failed to {normalised}: {result}")
                return False

    except Exception as e:
        print(f"⚠️  SMS exception for {normalised}: {e}")
        return False

async def send_payment_confirmation(
    trader_phone: str,
    amount_ngn: float,
    amount_sats: int,
) -> bool:

    message = (
        f"KoboSats: Payment received!\n"
        f"Amount: \u20a6{amount_ngn:,.0f} ({amount_sats:,} sats)\n"
        f"Your wallet has been updated.\n"
        f"Powered by Bitcoin Lightning."
    )
    return await send_sms(trader_phone, message)


async def send_debt_reminder(
    debtor_phone: str,
    creditor_name: str,
    amount_ngn: float,
    description: str,
) -> bool:
    
    message = (
        f"Reminder from {creditor_name} via KoboSats:\n"
        f"You owe \u20a6{amount_ngn:,.0f} for: {description}\n"
        f"Please pay at your earliest convenience.\n"
        f"Reply STOP to opt out."
    )
    return await send_sms(debtor_phone, message)


async def send_debt_logged_confirmation(
    trader_phone: str,
    debtor_phone: str,
    amount_ngn: float,
    description: str,
) -> bool:

    message = (
        f"KoboSats: Debt logged\n"
        f"Customer: {debtor_phone}\n"
        f"Amount: \u20a6{amount_ngn:,.0f}\n"
        f"For: {description}\n"
        f"You can send a reminder anytime."
    )
    return await send_sms(trader_phone, message)


async def send_debt_settled_confirmation(
    trader_phone: str,
    debtor_phone: str,
    amount_ngn: float,
) -> bool:

    message = (
        f"KoboSats: Debt settled \u2705\n"
        f"Customer: {debtor_phone}\n"
        f"Amount: \u20a6{amount_ngn:,.0f}\n"
        f"This debt is now closed."
    )
    return await send_sms(trader_phone, message)