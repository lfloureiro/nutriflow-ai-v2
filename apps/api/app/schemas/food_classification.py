import uuid

from pydantic import BaseModel


class FoodItemClassificationRead(BaseModel):
    id: uuid.UUID
    classification_type: str
    classification_key: str
    source: str
    source_reference: str | None
