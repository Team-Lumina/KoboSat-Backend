SATS_PER_BTC = 100_000_000


def ngn_to_sats(amount_ngn: float, btc_ngn_rate: float) -> int:
    if btc_ngn_rate <= 0:
        raise ValueError("BTC/NGN rate must be a positive number")
    if amount_ngn <= 0:
        raise ValueError("Amount must be a positive number")

    btc_amount = amount_ngn / btc_ngn_rate
    sats = int(btc_amount * SATS_PER_BTC)
    return sats


def sats_to_ngn(amount_sats: float, btc_ngn_rate: float) -> float:
    if btc_ngn_rate <= 0:
        raise ValueError("BTC/NGN rate must be a positive number")

    btc_amount = amount_sats / SATS_PER_BTC
    ngn = btc_amount * btc_ngn_rate
    return round(ngn, 2)


def format_naira(amount: float) -> str:
    return f"\u20a6{amount:,.2f}"


def format_sats(amount: int) -> str:
    return f"{amount:,} sats"