from decimal import ROUND_HALF_UP, Decimal

RATING_QUANTUM = Decimal("0.01")
OUTLIER_PENALTY = Decimal("0.15")
MIN_RATINGS_FOR_OUTLIER_SOFTENING = 4
ZERO = Decimal(0)
FIVE = Decimal(5)


def effective_family_rating(ratings: list[Decimal]) -> Decimal:
    if not ratings:
        return ZERO

    ordered = sorted(ratings, reverse=True)
    if len(ordered) < MIN_RATINGS_FOR_OUTLIER_SOFTENING:
        value = sum(ordered, start=ZERO) / Decimal(len(ordered))
    else:
        lowest = ordered[-1]
        base_values = ordered[:-1]
        base = sum(base_values, start=ZERO) / Decimal(len(base_values))
        disagreement_penalty = (base - lowest) * OUTLIER_PENALTY
        value = base - disagreement_penalty

    return max(ZERO, min(FIVE, value)).quantize(
        RATING_QUANTUM,
        rounding=ROUND_HALF_UP,
    )
