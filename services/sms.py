import africastalking
from config import settings

try:
    africastalking.initialize(
        username=settings.AT_USERNAME,
        api_key=settings.AT_API_KEY,
    )
    sms_client = africastalking.SMS
    AT_AVAILABLE = True
    print("✅ Africa's Talking SMS ready")
except Exception as e:
    sms_client = None
    AT_AVAILABLE = False
    print(f"⚠️  Africa's Talking init failed: {e}")

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
    if not AT_AVAILABLE or not sms_client:
        # Print to console so you can see what would have been sent
        print(f"[SMS NOT SENT — AT unavailable]")
        print(f"  To:      {phone}")
        print(f"  Message: {message}")
        return False

    normalised = normalise_phone(phone)

    try:
        response = sms_client.send(
            message=message,
            recipients=[normalised],
        )

        recipients = response.get("SMSMessageData", {}).get("Recipients", [])
        if recipients:
            status = recipients[0].get("status", "")
            if status == "Success":
                print(f"📱 SMS sent to {normalised}")
                return True
            else:
                print(f"⚠️  SMS failed to {normalised}: {status}")
                return False
        else:
            print(f"⚠️  SMS response had no recipients: {response}")
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