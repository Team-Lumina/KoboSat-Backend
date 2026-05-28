import re


def validate_phone(phone: str) -> str | None:

    if not phone or not isinstance(phone, str):
        return None

    cleaned = (
        phone.strip()
        .replace(" ", "")
        .replace("-", "")
        .replace("(", "")
        .replace(")", "")
    )

    if re.match(r"^\+234[7-9]\d{9}$", cleaned):
        return cleaned

    if re.match(r"^234[7-9]\d{9}$", cleaned):
        return f"+{cleaned}"

    if re.match(r"^0[7-9]\d{9}$", cleaned):
        return f"+234{cleaned[1:]}"

    if re.match(r"^[7-9]\d{9}$", cleaned):
        return f"+234{cleaned}"

    return None


def validate_amount(amount) -> float | None:

    try:
        if isinstance(amount, str):
            amount = amount.replace(",", "").strip()

        value = float(amount)

        if value <= 0:
            return None

        if value > 10_000_000:
            return None

        return value

    except (ValueError, TypeError):
        return None


def validate_language(language: str) -> str | None:
    supported = ("en", "yo", "ha", "ig")
    if language and language.lower() in supported:
        return language.lower()
    return None