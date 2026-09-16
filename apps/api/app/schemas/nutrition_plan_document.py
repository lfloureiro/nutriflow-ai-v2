from pydantic import BaseModel, Field


class NutritionPlanDocumentExtractionRead(BaseModel):
    filename: str
    content_type: str | None
    document_type: str
    source_text: str = Field(min_length=1)
    character_count: int = Field(ge=1)
    extractor_name: str
    extractor_version: str
    warnings: list[str]
