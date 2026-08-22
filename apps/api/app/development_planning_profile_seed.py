import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.family import Family
from app.models.food_catalog import FoodItem, Recipe
from app.models.meal_candidate_planning_profile import MealCandidatePlanningProfile

PROFILE_NAMESPACE = uuid.UUID("91690f69-c0cc-4a4d-bcba-0f59ef0f0344")
SOURCE_REFERENCE = "nutriflow-v2-development-planning-profiles"


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
    PlanningProfileDefinition("recipe", "legacy-v1:recipe:1", "meat", "beef"),
    PlanningProfileDefinition("recipe", "legacy-v1:recipe:2", "meat", "beef"),
    PlanningProfileDefinition("recipe", "legacy-v1:recipe:3", "meat", "chicken"),
    PlanningProfileDefinition("recipe", "legacy-v1:recipe:5", "fish", "salmon"),
    PlanningProfileDefinition("recipe", "legacy-v1:recipe:6", "meat", "chicken"),
    PlanningProfileDefinition("food_item", "demo:massa-bolonhesa", "meat", "beef"),
    PlanningProfileDefinition("food_item", "demo:frango-arroz-legumes", "meat", "chicken"),
    PlanningProfileDefinition("food_item", "demo:salmao-batata-salada", "fish", "salmon"),
    PlanningProfileDefinition("food_item", "demo:vaca-ostras-arroz", "meat", "beef"),
    PlanningProfileDefinition("food_item", "demo:salada-grao-atum-ovo", "fish", "tuna"),
    PlanningProfileDefinition("food_item", "demo:pizza-pepperoni", "meat", "processed_meat"),
)


def _profile_id(definition: PlanningProfileDefinition) -> uuid.UUID:
    return uuid.uuid5(
        PROFILE_NAMESPACE,
        f"{definition.candidate_kind}:{definition.candidate_key}",
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
                FoodItem.family_id == family.id,
            )
        )
    else:
        candidate = session.scalar(
            select(Recipe).where(
                Recipe.recipe_key == definition.candidate_key,
                Recipe.family_id == family.id,
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
) -> DevelopmentPlanningProfileSeedResult:
    for definition in PROFILE_DEFINITIONS:
        candidate = _candidate(session, family, definition)
        profile_id = _profile_id(definition)
        profile = session.get(MealCandidatePlanningProfile, profile_id)
        if profile is None:
            profile = MealCandidatePlanningProfile(id=profile_id, family=family)
            session.add(profile)

        profile.candidate_kind = definition.candidate_kind
        profile.food_item_id = candidate.id if definition.candidate_kind == "food_item" else None
        profile.recipe_id = candidate.id if definition.candidate_kind == "recipe" else None
        profile.planning_category = definition.planning_category
        profile.primary_protein = definition.primary_protein
        profile.suitable_meal_types = list(definition.suitable_meal_types)
        profile.auto_plan_enabled = True
        profile.source = "demo"
        profile.source_reference = SOURCE_REFERENCE

    session.flush()
    return DevelopmentPlanningProfileSeedResult(profile_count=len(PROFILE_DEFINITIONS))
