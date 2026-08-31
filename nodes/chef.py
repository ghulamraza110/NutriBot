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


def chef_node(state: RecipeState) -> dict:
    ingredients = state["ingredients"]
    critique = state.get("critique", "")
    iteration = state.get("iteration", 0) + 1

    system = (
        "You are a professional chef. Create a realistic, cookable recipe "
        "using only the given ingredients (plus basic pantry staples like "
        "salt, pepper, oil, and water). Be specific with steps and cooking times."
    )

    if critique:
        user = (
            f"Ingredients: {ingredients}\n\n"
            f"Your previous recipe was rejected. Fix these issues:\n{critique}\n\n"
            f"Write an improved recipe."
        )
    else:
        user = f"Ingredients: {ingredients}\n\nWrite a complete recipe."

    response = llm.invoke(
        [
            SystemMessage(content=system),
            HumanMessage(content=user),
        ]
    )

    return {
        "recipe_proposal": response.content,
        "iteration": iteration,
    }
