from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from models.inspector_result import InspectorResult
from models.state import RecipeState

load_dotenv()

llm = ChatOpenAI(
    model="openai/gpt-4o-mini",
    base_url="https://openrouter.ai/api/v1",
    max_tokens=2000,
    temperature=0,
)
inspector_llm = llm.with_structured_output(InspectorResult)


async def inspector_node(state: RecipeState) -> dict:
    recipe = state["recipe_proposal"]
    ingredients = state["ingredients"]

    system = (
        "You are a food safety inspector. Evaluate recipes for:\n"
        "1. Food safety (cooking temps, cross-contamination, toxic combos)\n"
        "2. Realism (actually cookable, reasonable times)\n"
        "3. Ingredient match (recipe should use the provided ingredients)\n\n"
        "Set is_safe to true only if the recipe passes all checks. "
        "If unsafe, provide a clear critique and list specific concerns."
    )

    user = (
        f"Available ingredients: {ingredients}\n\n"
        f"Recipe to evaluate:\n{recipe}"
    )

    result: InspectorResult = await inspector_llm.ainvoke([
        SystemMessage(content=system),
        HumanMessage(content=user),
    ])

    critique = result.critique
    if not result.is_safe and result.concerns:
        concerns_text = "\n".join(f"- {c}" for c in result.concerns)
        critique = f"{critique}\n\nConcerns:\n{concerns_text}".strip()

    return {
        "is_safe": result.is_safe,
        "critique": critique,
    }
