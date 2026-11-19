import uuid
from dataclasses import dataclass

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.family import Family
from app.models.food_catalog import FoodItem, Recipe
from app.models.meal_candidate_planning_profile import MealCandidatePlanningProfile

PROFILE_NAMESPACE = uuid.UUID("91690f69-c0cc-4a4d-bcba-0f59ef0f0344")
SOURCE_REFERENCE = "nutriflow-v2-development-planning-profiles"
LOUREIRO_PROFILE_SOURCE = "legacy-v1"
LOUREIRO_PROFILE_SOURCE_REFERENCE = "nutriflow-v1-loureiro-structured-planning-traits-v1"


@dataclass(frozen=True)
class PlanningProfileDefinition:
    candidate_kind: str
    candidate_key: str
    planning_category: str
    primary_protein: str
    suitable_meal_types: tuple[str, ...] = ("lunch", "dinner")


@dataclass(frozen=True)
class DevelopmentPlanningProfileSeedResult:
    profile_count: int


PROFILE_DEFINITIONS = (
    PlanningProfileDefinition("recipe", "legacy-v1:recipe:1", "meat", "chicken"),
    PlanningProfileDefinition("recipe", "legacy-v1:recipe:2", "meat", "chicken"),
    PlanningProfileDefinition("recipe", "legacy-v1:recipe:3", "fish", "white_fish"),
    PlanningProfileDefinition("recipe", "legacy-v1:recipe:5", "meat", "beef"),
    PlanningProfileDefinition("recipe", "legacy-v1:recipe:6", "meat", "turkey"),
    PlanningProfileDefinition("food_item", "demo:massa-bolonhesa", "meat", "beef"),
    PlanningProfileDefinition("food_item", "demo:frango-arroz-legumes", "meat", "chicken"),
    PlanningProfileDefinition("food_item", "demo:salmao-batata-salada", "fish", "salmon"),
    PlanningProfileDefinition("food_item", "demo:vaca-ostras-arroz", "meat", "beef"),
    PlanningProfileDefinition("food_item", "demo:salada-grao-atum-ovo", "fish", "tuna"),
    PlanningProfileDefinition("food_item", "demo:pizza-pepperoni", "meat", "processed_meat"),
)


LOUREIRO_LEGACY_PROFILE_DEFINITIONS = (
    PlanningProfileDefinition("recipe", "legacy-v1:recipe:1", "meat", "chicken"),
    PlanningProfileDefinition("recipe", "legacy-v1:recipe:2", "meat", "chicken"),
    PlanningProfileDefinition("recipe", "legacy-v1:recipe:3", "fish", "white_fish"),
    PlanningProfileDefinition("recipe", "legacy-v1:recipe:4", "vegetarian_other", "cheese"),
    PlanningProfileDefinition("recipe", "legacy-v1:recipe:5", "meat", "beef"),
    PlanningProfileDefinition("recipe", "legacy-v1:recipe:6", "meat", "turkey"),
    PlanningProfileDefinition("recipe", "legacy-v1:recipe:7", "eggs", "egg"),
    PlanningProfileDefinition("recipe", "legacy-v1:recipe:8", "meat", "processed_meat"),
    PlanningProfileDefinition("recipe", "legacy-v1:recipe:9", "fish", "salmon"),
    PlanningProfileDefinition("recipe", "legacy-v1:recipe:10", "meat", "beef"),
    PlanningProfileDefinition("recipe", "legacy-v1:recipe:11", "fish", "hake"),
    PlanningProfileDefinition("recipe", "legacy-v1:recipe:12", "meat", "chicken"),
    PlanningProfileDefinition("recipe", "legacy-v1:recipe:13", "meat", "beef"),
    PlanningProfileDefinition("recipe", "legacy-v1:recipe:14", "meat", "chicken"),
    PlanningProfileDefinition("recipe", "legacy-v1:recipe:15", "meat", "beef"),
    PlanningProfileDefinition("recipe", "legacy-v1:recipe:16", "fish", "white_fish"),
    PlanningProfileDefinition("recipe", "legacy-v1:recipe:17", "fish", "cod"),
    PlanningProfileDefinition("recipe", "legacy-v1:recipe:18", "meat", "chicken"),
    PlanningProfileDefinition("recipe", "legacy-v1:recipe:19", "meat", "beef"),
    PlanningProfileDefinition("recipe", "legacy-v1:recipe:20", "meat", "beef"),
    PlanningProfileDefinition("recipe", "legacy-v1:recipe:21", "meat", "pork"),
    PlanningProfileDefinition("recipe", "legacy-v1:recipe:22", "fish", "hake"),
    PlanningProfileDefinition("recipe", "legacy-v1:recipe:23", "meat", "beef"),
    PlanningProfileDefinition("recipe", "legacy-v1:recipe:24", "fish", "hake"),
    PlanningProfileDefinition("recipe", "legacy-v1:recipe:25", "fish", "cod"),
    PlanningProfileDefinition("recipe", "legacy-v1:recipe:26", "fish", "cod"),
    PlanningProfileDefinition("recipe", "legacy-v1:recipe:27", "meat", "pork"),
    PlanningProfileDefinition("recipe", "legacy-v1:recipe:28", "meat", "pork"),
    PlanningProfileDefinition("recipe", "legacy-v1:recipe:29", "meat", "beef"),
    PlanningProfileDefinition("recipe", "legacy-v1:recipe:30", "meat", "chicken"),
    PlanningProfileDefinition("recipe", "legacy-v1:recipe:31", "fish", "hake"),
    PlanningProfileDefinition("recipe", "legacy-v1:recipe:32", "meat", "chicken"),
    PlanningProfileDefinition("recipe", "legacy-v1:recipe:33", "meat", "beef"),
    PlanningProfileDefinition("recipe", "legacy-v1:recipe:34", "meat", "pork"),
    PlanningProfileDefinition("recipe", "legacy-v1:recipe:35", "meat", "beef"),
    PlanningProfileDefinition("recipe", "legacy-v1:recipe:36", "meat", "rabbit"),
    PlanningProfileDefinition("recipe", "legacy-v1:recipe:37", "meat", "chicken"),
    PlanningProfileDefinition("recipe", "legacy-v1:recipe:38", "eggs", "egg"),
    PlanningProfileDefinition("recipe", "legacy-v1:recipe:39", "meat", "chicken"),
    PlanningProfileDefinition("recipe", "legacy-v1:recipe:40", "meat", "turkey"),
    PlanningProfileDefinition("recipe", "legacy-v1:recipe:41", "meat", "chicken"),
    PlanningProfileDefinition("recipe", "legacy-v1:recipe:42", "fish", "white_fish"),
    PlanningProfileDefinition("recipe", "legacy-v1:recipe:43", "fish", "salmon"),
)


def _profile_id(
    family_id: uuid.UUID,
    definition: PlanningProfileDefinition,
) -> uuid.UUID:
    return uuid.uuid5(
        PROFILE_NAMESPACE,
        f"{family_id}:{definition.candidate_kind}:{definition.candidate_key}",
    )


def _candidate(
    session: Session,
    family: Family,
    definition: PlanningProfileDefinition,
) -> FoodItem | Recipe:
    if definition.candidate_kind == "food_item":
        candidate = session.scalar(
            select(FoodItem).where(
                FoodItem.catalog_key == definition.candidate_key,
                or_(FoodItem.family_id.is_(None), FoodItem.family_id == family.id),
            )
        )
    else:
        candidate = session.scalar(
            select(Recipe).where(
                Recipe.recipe_key == definition.candidate_key,
                or_(Recipe.family_id.is_(None), Recipe.family_id == family.id),
            )
        )
    if candidate is None:
        raise RuntimeError(
            f"Development planning profile candidate {definition.candidate_key!r} is missing."
        )
    return candidate


def seed_development_planning_profiles(
    session: Session,
    *,
    family: Family,
    definitions: tuple[PlanningProfileDefinition, ...] = PROFILE_DEFINITIONS,
    source: str = "demo",
    source_reference: str = SOURCE_REFERENCE,
) -> DevelopmentPlanningProfileSeedResult:
    if family.id is None:
        raise RuntimeError("Development planning profiles require a persisted Family.")

    for definition in definitions:
        candidate = _candidate(session, family, definition)
        if definition.candidate_kind == "food_item":
            profile = session.scalar(
                select(MealCandidatePlanningProfile).where(
                    MealCandidatePlanningProfile.family_id == family.id,
                    MealCandidatePlanningProfile.food_item_id == candidate.id,
                )
            )
        else:
            profile = session.scalar(
                select(MealCandidatePlanningProfile).where(
                    MealCandidatePlanningProfile.family_id == family.id,
                    MealCandidatePlanningProfile.recipe_id == candidate.id,
                )
            )
        if profile is None:
            profile = MealCandidatePlanningProfile(
                id=_profile_id(family.id, definition),
                family=family,
            )
            session.add(profile)

        profile.candidate_kind = definition.candidate_kind
        profile.food_item_id = candidate.id if definition.candidate_kind == "food_item" else None
        profile.recipe_id = candidate.id if definition.candidate_kind == "recipe" else None
        profile.planning_category = definition.planning_category
        profile.primary_protein = definition.primary_protein
        profile.suitable_meal_types = list(definition.suitable_meal_types)
        profile.auto_plan_enabled = True
        profile.source = source
        profile.source_reference = source_reference

    session.flush()
    return DevelopmentPlanningProfileSeedResult(profile_count=len(definitions))
