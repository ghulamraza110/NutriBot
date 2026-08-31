import asyncio

from langgraph.graph import END, StateGraph

from models.recipe import Recipe
from models.state import RecipeState
from nodes.chef import chef_node
from nodes.inspector import inspector_node
from nodes.validator import validator_node
from utils.routing import route_after_validation, route_kitchen

workflow = StateGraph(RecipeState)
workflow.add_node("validator", validator_node)
workflow.add_node("chef", chef_node)
workflow.add_node("inspector", inspector_node)
workflow.add_edge("chef", "inspector")
workflow.add_conditional_edges(
    "validator",
    route_after_validation,
    {"reject": END, "continue": "chef"},
)
workflow.add_conditional_edges(
    "inspector", route_kitchen, {"serve": END, "recook": "chef", "stop": END}
)
workflow.set_entry_point("validator")
app = workflow.compile()


def format_recipe(recipe_json: str) -> str:
    recipe = Recipe.model_validate_json(recipe_json)
    lines = [
        f"Title: {recipe.title}",
        f"Servings: {recipe.servings} | Cook time: {recipe.cook_time_minutes} min",
        "",
        "Steps:",
    ]
    for i, step in enumerate(recipe.steps, start=1):
        lines.append(f"  {i}. {step}")
    return "\n".join(lines)


def make_initial_state(ingredients: str) -> RecipeState:
    return {
        "ingredients": ingredients,
        "recipe_proposal": "",
        "is_safe": False,
        "critique": "",
        "iteration": 0,
    }


def print_result(result: RecipeState) -> None:
    print("\n--- FINAL RESULT ---")
    print(f"Safe: {result['is_safe']}")
    print(f"Iterations: {result['iteration']}")

    if result.get("critique") and not result.get("recipe_proposal"):
        print(f"\nInput rejected:\n{result['critique']}")
    else:
        print(f"\nRecipe:\n{format_recipe(result['recipe_proposal'])}")
        if result.get("critique"):
            print(f"\nLast critique:\n{result['critique']}")


async def run_meal_planner(state: RecipeState) -> RecipeState:
    return await app.ainvoke(state)


async def run_batch(states: list[RecipeState]) -> list[RecipeState]:
    return await asyncio.gather(*(app.ainvoke(state) for state in states))


async def main() -> None:
    state = make_initial_state("chicken, rice, onion, tomato")
    result = await run_meal_planner(state)
    print_result(result)


if __name__ == "__main__":
    asyncio.run(main())
