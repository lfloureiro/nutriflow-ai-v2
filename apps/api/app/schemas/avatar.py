from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class AvatarAppearance(BaseModel):
    """Presentation choices only; never inputs to nutrition or health calculations."""

    model_config = ConfigDict(extra="forbid")

    stage: Literal["child", "teen", "young", "adult", "mature", "senior", "unknown"] | None = None
    style: Literal["male", "female", "neutral"] | None = None
    variant: int | None = Field(default=None, ge=0, le=5, strict=True)
