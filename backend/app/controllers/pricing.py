"""Pure surge-pricing rule; the stored hotel rate is never changed."""

from decimal import Decimal, ROUND_HALF_UP

from ..models import PriceQuote


def quote(base_rate: int, matching_searches_today: int) -> PriceQuote:
    surged = matching_searches_today >= 4
    multiplier = Decimal("1.20") if surged else Decimal("1.00")
    displayed = (Decimal(base_rate) * multiplier).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return PriceQuote(
        base_nightly_rate_usd=base_rate,
        displayed_nightly_rate_usd=float(displayed),
        matching_searches_today=matching_searches_today,
        surge_applied=surged,
    )
