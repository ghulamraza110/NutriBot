from typing import TypedDict


class RecipeState(TypedDict):
    ingredients: str
    recipe_proposal: str
    is_safe: bool
    critique: str
    iteration: int
    rejection_type: str
