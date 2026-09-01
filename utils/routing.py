from langsmith import traceable

from models.state import RecipeState


@traceable(name="route_after_validation", run_type="chain")
def route_after_validation(state: RecipeState) -> str:
    if state.get("critique") and not state.get("recipe_proposal"):
        return "reject"
    return "continue"


@traceable(name="route_kitchen", run_type="chain")
def route_kitchen(state: RecipeState) -> str:
    if state.get("iteration", 0) >= 3:
        return "stop"
    if state.get("is_safe"):
        return "serve"
    return "recook"
