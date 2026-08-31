from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from models.state import RecipeState

load_dotenv()

llm = ChatOpenAI(
    model="openai/gpt-4o-mini",
    base_url="https://openrouter.ai/api/v1",
    max_tokens=2000,  # <--- ADD THIS LINE to lower the required credit reservation
    temperature=0.7,
)


def inspector_node(state: RecipeState) -> dict:
    recipe = state["recipe_proposal"]
    ingredients = state["ingredients"]

    system = (
        "You are a food safety inspector. Evaluate recipes for:\n"
        "1. Food safety (cooking temps, cross-contamination, toxic combos)\n"
        "2. Realism (actually cookable, reasonable times)\n"
        "3. Ingredient match (recipe should use the provided ingredients)\n\n"
        "Reply in EXACTLY this format:\n"
        "SAFE: yes\n"
        "or\n"
        "SAFE: no\n"
        "CRITIQUE: <specific issues to fix>"
    )

    user = f"Available ingredients: {ingredients}\n\n" f"Recipe to evaluate:\n{recipe}"

    response = llm.invoke(
        [
            SystemMessage(content=system),
            HumanMessage(content=user),
        ]
    )

    text = response.content.strip().lower()
    is_safe = "safe: yes" in text

    critique = ""
    if not is_safe:
        for line in response.content.splitlines():
            if line.lower().startswith("critique:"):
                critique = line.split(":", 1)[1].strip()
                break
        if not critique:
            critique = response.content

    return {
        "is_safe": is_safe,
        "critique": critique,
    }
