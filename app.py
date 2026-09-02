import asyncio
import sqlite3
import uuid

from langgraph.graph import END, StateGraph

from models.recipe import Recipe
from models.state import RecipeState
from nodes.chef import chef_node
from nodes.inspector import inspector_node
from nodes.validator import validator_node
from utils.persistence import CHECKPOINT_DB, compiled_app
from utils.routing import route_after_validation, route_kitchen
from utils.tracing import make_run_config, setup_langsmith

setup_langsmith()

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
        "rejection_type": "",
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


async def run_meal_planner(
    state: RecipeState,
    run_name: str = "meal-planner",
    thread_id: str | None = None,
) -> RecipeState:
    thread_id = thread_id or str(uuid.uuid4())
    config = make_run_config(state, run_name=run_name, thread_id=thread_id)

    async with compiled_app(workflow) as app:
        return await app.ainvoke(state, config=config)


async def get_thread_state(thread_id: str) -> RecipeState | None:
    config = {"configurable": {"thread_id": thread_id}}

    async with compiled_app(workflow) as app:
        snapshot = await app.aget_state(config)
        if not snapshot.values:
            return None
        return snapshot.values


def list_saved_threads(limit: int = 10) -> list[str]:
    """Return recent thread IDs that have checkpoint data."""
    try:
        conn = sqlite3.connect(CHECKPOINT_DB)
        rows = conn.execute(
            """
            SELECT thread_id
            FROM checkpoints
            GROUP BY thread_id
            ORDER BY MAX(rowid) DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        conn.close()
        return [row[0] for row in rows]
    except sqlite3.Error:
        return []


async def run_batch(states: list[RecipeState]) -> list[RecipeState]:
    return await asyncio.gather(
        *(
            run_meal_planner(state, run_name=f"meal-planner-{i}", thread_id=str(uuid.uuid4()))
            for i, state in enumerate(states)
        )
    )


async def main() -> None:
    thread_id = "demo-session"
    state = make_initial_state("chicken, rice, onion, tomato")
    result = await run_meal_planner(state, thread_id=thread_id)
    print_result(result)

    saved = await get_thread_state(thread_id)
    if saved:
        print(f"\n--- PERSISTED STATE (thread: {thread_id}) ---")
        print(f"Safe: {saved['is_safe']}")
        print(f"Iterations: {saved['iteration']}")
        print(f"Ingredients: {saved['ingredients']}")


if __name__ == "__main__":
    asyncio.run(main())
