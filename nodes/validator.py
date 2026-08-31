from models.state import RecipeState

BLOCKLIST = {
    "bleach",
    "ammonia",
    "detergent",
    "soap",
    "gasoline",
    "acetone",
    "pesticide",
    "rat poison",
}


def validator_node(state: RecipeState) -> dict:
    ingredients = state["ingredients"].strip()

    if len(ingredients) < 3:
        return {
            "is_safe": False,
            "critique": "Invalid input: ingredients list is too short.",
        }

    if not any(char.isalpha() for char in ingredients):
        return {
            "is_safe": False,
            "critique": "Invalid input: please provide real ingredient names.",
        }

    lowered = ingredients.lower()
    for blocked in BLOCKLIST:
        if blocked in lowered:
            return {
                "is_safe": False,
                "critique": f"Rejected: '{blocked}' is not a valid cooking ingredient.",
            }

    return {}
