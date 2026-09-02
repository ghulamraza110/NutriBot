from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langsmith import traceable

from models.recipe import Recipe
from models.state import RecipeState

load_dotenv()

llm = ChatOpenAI(
    model="openai/gpt-4o-mini",
    base_url="https://openrouter.ai/api/v1",
    max_tokens=2000,
    temperature=0.7,
)
chef_llm = llm.with_structured_output(Recipe)


@traceable(name="chef_node", run_type="chain")
async def chef_node(state: RecipeState) -> dict:
    ingredients = state["ingredients"]
    critique = state.get("critique", "")
    iteration = state.get("iteration", 0) + 1

    system = (
        "You are a professional chef. Create a realistic, cookable recipe "
        "using only safe, edible versions of the given ingredients (plus basic "
        "pantry staples like salt, oil, and water).\n\n"
        "NEVER create recipes that use:\n"
        "- medicine, chemicals, or non-food items\n"
        "- expired, rotten, or spoiled ingredients\n"
        "- wild or dangerous animals (snakes, rodents, etc.)\n"
        "- any ingredient the user says they are allergic to\n"
        "- weapons, explosives, or any non-food requests\n\n"
        "Only create food recipes. Be specific with steps and cooking times."
    )

    if critique:
        user = (
            f"Ingredients: {ingredients}\n\n"
            f"Your previous recipe was rejected. Fix these issues:\n{critique}\n\n"
            f"Write an improved recipe."
        )
    else:
        user = f"Ingredients: {ingredients}\n\nWrite a complete recipe."

    recipe: Recipe = await chef_llm.ainvoke([
        SystemMessage(content=system),
        HumanMessage(content=user),
    ])

    return {
        "recipe_proposal": recipe.model_dump_json(indent=2),
        "iteration": iteration,
    }
