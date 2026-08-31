from models.state import RecipeState


def route_kitchen(state: RecipeState) -> str:
    if state.get("iteration", 0) >= 3:
        return "stop"
    if state.get("is_safe"):
        return "serve"
    return "recook"
