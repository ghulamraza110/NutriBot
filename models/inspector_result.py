from pydantic import BaseModel, Field


class InspectorResult(BaseModel):
    is_safe: bool
    critique: str = ""
    concerns: list[str] = Field(default_factory=list)
