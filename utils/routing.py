from models.state import RecipeState


def route_after_validation(state: RecipeState) -> str:
    if state.get("critique") and not state.get("recipe_proposal"):
        return "reject"
    return "continue"


def route_kitchen(state: RecipeState) -> str:
    if state.get("iteration", 0) >= 3:
        return "stop"
    if state.get("is_safe"):
        return "serve"
    return "recook"
