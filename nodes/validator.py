import re

from langsmith import traceable

from models.state import RecipeState
from utils.messages import OUT_OF_CONTEXT_MESSAGE

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

NON_FOOD_KEYWORDS = {
    "medicine",
    "medication",
    "pill",
    "pills",
    "tablet",
    "capsule",
    "drug",
    "drugs",
    "poison",
    "chemical",
    "fertilizer",
    "insecticide",
    "herbicide",
    "lubricant",
    "paint",
    "glue",
    "detergent",
    "disinfectant",
}

UNSAFE_FOOD_KEYWORDS = {
    "expired",
    "rotten",
    "moldy",
    "mouldy",
    "spoiled",
    "rancid",
    "spoilt",
}

NON_EDIBLE_ANIMALS = {
    "mamba",
    "snake",
    "rat",
    "mouse",
    "bat",
    "frog",
    "toad",
    "insect",
    "worm",
    "larvae",
}

WEAPONS_PHRASES = (
    "atom bomb",
    "atomic bomb",
    "nuclear bomb",
    "pipe bomb",
    "car bomb",
    "dirty bomb",
    "make a bomb",
    "build a bomb",
    "how to make a bomb",
)

WEAPONS_KEYWORDS = {
    "bomb",
    "explosive",
    "explosives",
    "grenade",
    "weapon",
    "weapons",
    "firearm",
    "ammunition",
    "uranium",
    "plutonium",
    "dynamite",
    "missile",
    "tnt",
}

FOOD_HINTS = {
    "chicken", "beef", "pork", "lamb", "fish", "salmon", "tuna", "shrimp",
    "rice", "pasta", "noodle", "egg", "eggs", "milk", "cheese", "butter",
    "onion", "tomato", "potato", "carrot", "bread", "garlic", "ginger",
    "pepper", "salt", "sugar", "flour", "oil", "vegetable", "fruit", "bean",
    "lentil", "tofu", "mushroom", "spinach", "broccoli", "corn", "peas",
    "soup", "salad", "meat", "turkey", "duck", "yogurt", "cream",
    "honey", "lemon", "lime", "apple", "banana", "avocado", "cucumber",
}

NON_COOKING_TOPICS = {
    "weather", "football", "soccer", "cricket", "bitcoin", "crypto", "stock",
    "homework", "essay", "python", "javascript", "code", "programming",
    "politics", "election", "president", "movie", "film", "song", "music",
    "relationship", "dating", "travel", "flight", "hotel", "computer",
    "laptop", "phone", "wifi", "doctor", "hospital", "math", "physics",
    "history", "geography", "capital of", "prime minister", "elon musk",
}

OFF_TOPIC_PATTERNS = (
    re.compile(r"\btell me (?:about|how to)\b", re.IGNORECASE),
    re.compile(r"\bhow (?:do i|to) (?:make|build|create|fix|hack)\b", re.IGNORECASE),
    re.compile(r"\bi want to (?:make|build|create|know|learn)\b", re.IGNORECASE),
    re.compile(r"\bwhat is\b", re.IGNORECASE),
    re.compile(r"\bwho is\b", re.IGNORECASE),
    re.compile(r"\bexplain\b", re.IGNORECASE),
    re.compile(r"\bhelp me with\b", re.IGNORECASE),
    re.compile(r"\bwrite (?:a|an|me)\b", re.IGNORECASE),
)

QUESTION_PATTERNS = (
    re.compile(r"^\s*(what|who|when|where|why|how|can you|could you|please)\b", re.IGNORECASE),
    re.compile(r"\?\s*$"),
)

ALLERGY_PATTERN = re.compile(
    r"(?:allergic to|allergy to|cannot eat|can't eat|avoid)\s+([^,.;]+)",
    re.IGNORECASE,
)


def _find_keyword(text: str, keywords: set[str]) -> str | None:
    for keyword in keywords:
        if keyword in {"capital of", "prime minister", "elon musk"}:
            if keyword in text:
                return keyword
        elif re.search(rf"\b{re.escape(keyword)}\b", text):
            return keyword
    return None


def _looks_like_food_input(text: str) -> bool:
    lowered = text.lower()
    if _find_keyword(lowered, FOOD_HINTS):
        return True
    parts = [part.strip() for part in re.split(r"[,;]+", lowered) if part.strip()]
    return len(parts) >= 2 and all(len(part) < 40 for part in parts)


def _is_out_of_context(text: str) -> bool:
    lowered = text.lower()
    if _looks_like_food_input(lowered):
        return False
    if _find_keyword(lowered, NON_COOKING_TOPICS):
        return True
    if any(pattern.search(lowered) for pattern in OFF_TOPIC_PATTERNS):
        return True
    if any(pattern.search(lowered) for pattern in QUESTION_PATTERNS):
        return True
    return len(lowered.split()) >= 5


def validate_ingredients(ingredients: str) -> tuple[str, str] | None:
    """Return (message, rejection_type) if invalid, else None."""
    text = ingredients.strip()
    lowered = text.lower()

    if len(text) < 3:
        return "Invalid input: ingredients list is too short.", "unsafe"

    if not any(char.isalpha() for char in text):
        return "Invalid input: please provide real ingredient names.", "unsafe"

    if any(phrase in lowered for phrase in WEAPONS_PHRASES):
        return OUT_OF_CONTEXT_MESSAGE, "out_of_context"

    if _find_keyword(lowered, WEAPONS_KEYWORDS):
        return OUT_OF_CONTEXT_MESSAGE, "out_of_context"

    if _is_out_of_context(text):
        return OUT_OF_CONTEXT_MESSAGE, "out_of_context"

    blocked = _find_keyword(lowered, BLOCKLIST)
    if blocked:
        return f"Rejected: '{blocked}' is not a valid cooking ingredient.", "unsafe"

    non_food = _find_keyword(lowered, NON_FOOD_KEYWORDS)
    if non_food:
        return (
            f"Rejected: '{non_food}' is not food — medicines and chemicals cannot be used in recipes.",
            "unsafe",
        )

    unsafe_food = _find_keyword(lowered, UNSAFE_FOOD_KEYWORDS)
    if unsafe_food:
        return f"Rejected: '{unsafe_food}' ingredients are unsafe to cook with.", "unsafe"

    if re.search(r"\bdead\b", lowered):
        return "Rejected: do not use dead or unfit animals/ingredients in recipes.", "unsafe"

    non_edible = _find_keyword(lowered, NON_EDIBLE_ANIMALS)
    if non_edible:
        return f"Rejected: '{non_edible}' is not a safe or standard food ingredient.", "unsafe"

    for match in ALLERGY_PATTERN.finditer(text):
        allergen = match.group(1).strip().lower()
        if allergen and re.search(rf"\b{re.escape(allergen)}\b", lowered):
            return (
                (
                    f"Rejected: you listed '{allergen}' but also said you are allergic to it. "
                    f"Remove the allergen from your ingredients."
                ),
                "unsafe",
            )

    return None


@traceable(name="validator_node", run_type="chain")
async def validator_node(state: RecipeState) -> dict:
    result = validate_ingredients(state["ingredients"])
    if result:
        message, rejection_type = result
        return {
            "is_safe": False,
            "critique": message,
            "rejection_type": rejection_type,
        }
    return {"rejection_type": ""}
