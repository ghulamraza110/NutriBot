from pydantic import BaseModel, Field


class Recipe(BaseModel):
    title: str
    steps: list[str]
    cook_time_minutes: int = Field(ge=1)
    servings: int = Field(ge=1)
