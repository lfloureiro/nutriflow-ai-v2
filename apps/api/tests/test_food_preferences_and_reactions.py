from datetime import date

from sqlalchemy.orm import Session

from app.models.family import Family
from app.models.food_adverse_reaction import FoodAdverseReaction
from app.models.food_preference import FoodPreference
from app.models.person import Person


def test_food_preferences_and_adverse_reactions_are_separate(db_session: Session) -> None:
    family = Family(
        name="Food Domain Test Family",
        timezone="Europe/Lisbon",
    )

    person = Person(
        family=family,
        first_name="Food",
        last_name="Tester",
        birth_date=date(1990, 1, 1),
        preferred_locale="pt-PT",
        timezone="Europe/Lisbon",
    )

    pasta_like = FoodPreference(
        person=person,
        subject_type="dish_category",
        subject_key="pasta",
        preference_type="like",
        intensity=5,
        start_date=date(2026, 8, 21),
    )

    mushroom_dislike = FoodPreference(
        person=person,
        subject_type="ingredient",
        subject_key="mushroom",
        preference_type="dislike",
        intensity=4,
    )

    peanut_allergy = FoodAdverseReaction(
        person=person,
        reaction_type="allergy",
        subject_type="ingredient",
        subject_key="peanut",
        severity="severe",
        is_mandatory=True,
        source="doctor",
        source_name="Test Doctor",
        start_date=date(2026, 8, 21),
    )

    lactose_intolerance = FoodAdverseReaction(
        person=person,
        reaction_type="intolerance",
        subject_type="component",
        subject_key="lactose",
        severity="moderate",
        is_mandatory=False,
        source="user",
    )

    db_session.add(person)
    db_session.flush()

    assert person.id is not None
    assert pasta_like.id is not None
    assert mushroom_dislike.id is not None
    assert peanut_allergy.id is not None
    assert lactose_intolerance.id is not None

    assert pasta_like.source == "user"
    assert pasta_like.intensity == 5
    assert mushroom_dislike.preference_type == "dislike"

    assert peanut_allergy.reaction_type == "allergy"
    assert peanut_allergy.is_mandatory is True
    assert peanut_allergy.source == "doctor"

    assert lactose_intolerance.reaction_type == "intolerance"
    assert lactose_intolerance.is_mandatory is False

    db_session.expire(person, ["food_preferences", "food_adverse_reactions"])

    preferences = person.food_preferences
    reactions = person.food_adverse_reactions

    assert len(preferences) == 2
    assert len(reactions) == 2

    preference_by_key = {preference.subject_key: preference for preference in preferences}
    reaction_by_key = {reaction.subject_key: reaction for reaction in reactions}

    assert preference_by_key["pasta"].preference_type == "like"
    assert preference_by_key["mushroom"].preference_type == "dislike"

    assert reaction_by_key["peanut"].severity == "severe"
    assert reaction_by_key["peanut"].is_mandatory is True
    assert reaction_by_key["lactose"].reaction_type == "intolerance"
