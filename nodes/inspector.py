from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langsmith import traceable

from models.inspector_result import InspectorResult
from models.state import RecipeState
from utils.messages import OUT_OF_CONTEXT_MESSAGE

load_dotenv()

llm = ChatOpenAI(
    model="openai/gpt-4o-mini",
    base_url="https://openrouter.ai/api/v1",
    max_tokens=2000,
    temperature=0,
)
inspector_llm = llm.with_structured_output(InspectorResult)


@traceable(name="inspector_node", run_type="chain")
async def inspector_node(state: RecipeState) -> dict:
    recipe = state["recipe_proposal"]
    ingredients = state["ingredients"]

    system = (
        "You are a food safety inspector. Evaluate recipes for:\n"
        "1. Food safety (cooking temps, cross-contamination, toxic combos)\n"
        "2. Realism (actually cookable, reasonable times)\n"
        "3. Ingredient match (recipe should use the provided ingredients)\n"
        "4. No medicines, chemicals, or non-food items\n"
        "5. No expired, rotten, or spoiled ingredients\n"
        "6. No wild/dangerous animals (snakes, rodents, etc.)\n"
        "7. Respect allergies stated in the ingredient list (e.g. 'allergic to pepper')\n"
        "8. Reject weapons, explosives, drugs, or any non-food harmful requests\n"
        "9. Reject recipes when the user input is not about cooking food\n\n"
        f"If the request is not about recipes or cooking, set is_safe to false and use this critique:\n"
        f'"{OUT_OF_CONTEXT_MESSAGE}"\n\n'
        "Set is_safe to true only if the recipe passes all checks. "
        "If unsafe, provide a clear critique and list specific concerns."
        "Important rule (strict): If the user asks for something out of context (not related to cooking or recipes), do NOT generate a recipe. Instead, respond only with:"
        "Please only ask relevant cooking-related questions."
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

    rejection_type = ""
    if not result.is_safe and critique.strip().startswith("I don't have that information"):
        rejection_type = "out_of_context"

    return {
        "is_safe": result.is_safe,
        "critique": critique,
        "rejection_type": rejection_type,
    }
