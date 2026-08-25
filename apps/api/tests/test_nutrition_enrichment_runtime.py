from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session

from app.services import nutrition_enrichment_runtime
from app.services.portfir import PortfirFoodNutrition
from app.services.portfir_enrichment import PortfirAutoEnrichmentItem


def test_fresh_portfir_cache_does_not_download(tmp_path, monkeypatch) -> None:
    cache = tmp_path / "portfir.xlsx"
    cache.write_bytes(b"cached")

    def fail_download(_path) -> None:
        raise AssertionError("fresh cache must not download")

    monkeypatch.setattr(
        nutrition_enrichment_runtime,
        "download_portfir_workbook",
        fail_download,
    )

    resolved, refreshed = nutrition_enrichment_runtime.ensure_portfir_cache(
        path=cache,
        now=datetime.now(UTC),
    )

    assert resolved == cache
    assert refreshed is False


def test_stale_portfir_cache_is_refreshed(tmp_path, monkeypatch) -> None:
    cache = tmp_path / "portfir.xlsx"
    cache.write_bytes(b"old")
    observed_at = datetime.now(UTC)
    stale_timestamp = (observed_at - timedelta(days=31)).timestamp()
    cache.touch()
    cache.chmod(0o600)

    import os

    os.utime(cache, (stale_timestamp, stale_timestamp))
    calls: list[object] = []

    def fake_download(path) -> None:
        calls.append(path)
        path.write_bytes(b"new")

    monkeypatch.setattr(
        nutrition_enrichment_runtime,
        "download_portfir_workbook",
        fake_download,
    )

    resolved, refreshed = nutrition_enrichment_runtime.ensure_portfir_cache(
        path=cache,
        now=observed_at,
    )

    assert resolved == cache
    assert refreshed is True
    assert calls == [cache]


def test_runtime_summarizes_safe_auto_enrichment(
    db_session: Session,
    tmp_path,
    monkeypatch,
) -> None:
    cache = tmp_path / "portfir.xlsx"
    cache.write_bytes(b"cached")
    food = PortfirFoodNutrition(
        code="A1",
        name="Azeite",
        energy_kcal=Decimal("899"),
        nutrients=(),
    )
    enrichment = (
        PortfirAutoEnrichmentItem(
            catalog_key="legacy-v1:ingredient:olive-oil",
            name="Azeite",
            status="applied",
            matched_code="A1",
            matched_name="Azeite",
            confidence=Decimal(1),
            reason="exact_name",
            composition_created=True,
            recalculated_recipe_count=3,
        ),
        PortfirAutoEnrichmentItem(
            catalog_key="legacy-v1:ingredient:unknown",
            name="Ingrediente",
            status="review",
            matched_code="B1",
            matched_name="Outro",
            confidence=Decimal("0.80"),
            reason="fuzzy",
            composition_created=False,
            recalculated_recipe_count=0,
        ),
    )
    monkeypatch.setattr(
        nutrition_enrichment_runtime,
        "load_portfir_foods",
        lambda _path: (food,),
    )
    monkeypatch.setattr(
        nutrition_enrichment_runtime,
        "auto_enrich_shared_ingredients_from_portfir",
        lambda _db, *, foods, apply, limit: enrichment,
    )

    result = nutrition_enrichment_runtime.run_automatic_nutrition_enrichment(
        db_session,
        cache_path=cache,
    )

    assert result.source == "portfir"
    assert result.applied_count == 1
    assert result.review_count == 1
    assert result.unmatched_count == 0
    assert result.recalculated_recipe_count == 3
    assert result.items[0].composition_created is True
