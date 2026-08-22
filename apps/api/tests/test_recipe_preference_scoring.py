from decimal import Decimal

from app.services.recipe_preference_scoring import effective_family_rating


def test_effective_family_rating_softens_one_low_outlier_for_four_people() -> None:
    assert effective_family_rating(
        [Decimal(5), Decimal(5), Decimal(4), Decimal(1)]
    ) == Decimal("4.12")


def test_effective_family_rating_uses_plain_average_for_small_groups() -> None:
    assert effective_family_rating([Decimal(5), Decimal(1), Decimal(3)]) == Decimal("3.00")
