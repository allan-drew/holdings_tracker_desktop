from datetime import date, datetime
from decimal import Decimal

from holdings_tracker_desktop.ui.core import translations as i18n

def format_date(value: date) -> str:
    if not value:
        return ""

    fmt = i18n.get_date_format()

    return value.strftime(fmt)

def format_datetime(value: datetime) -> str:
    if not value:
        return ""

    date_fmt = i18n.get_date_format()
    time_fmt = i18n.get_time_format()

    return value.strftime(f"{date_fmt} {time_fmt}")

def format_decimal(value: Decimal, decimals: int = 2) -> str:
    if value is None:
        value = Decimal("0")

    fmt = f"{{:,.{decimals}f}}"
    text = fmt.format(value)

    fmt_cfg = i18n.get_number_format()

    if fmt_cfg["decimal"] == ",":
        text = text.replace(",", "X").replace(".", ",").replace("X", ".")

    return text

def format_quantity(value: Decimal, max_decimals: int = 6) -> str:
    """Format a quantity showing only the decimals it actually has (e.g. 100, 33.5)."""
    if value is None:
        value = Decimal("0")

    value = Decimal(value).quantize(Decimal(1).scaleb(-max_decimals)).normalize()
    decimals = max(-value.as_tuple().exponent, 0)

    return format_decimal(value, decimals)
