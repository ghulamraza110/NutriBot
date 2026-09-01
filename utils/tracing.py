import os
import uuid

from dotenv import load_dotenv

from models.state import RecipeState

DEFAULT_PROJECT = "meal-planner"


def setup_langsmith(project: str = DEFAULT_PROJECT) -> bool:
    """Enable LangSmith tracing when env vars are configured."""
    load_dotenv()

    api_key = os.getenv("LANGCHAIN_API_KEY") or os.getenv("LANGSMITH_API_KEY")
    if api_key and not os.getenv("LANGCHAIN_API_KEY"):
        os.environ["LANGCHAIN_API_KEY"] = api_key

    if not os.getenv("LANGCHAIN_PROJECT"):
        os.environ["LANGCHAIN_PROJECT"] = project

    tracing_enabled = os.getenv("LANGCHAIN_TRACING_V2", "").lower() in ("true", "1", "yes")
    if not tracing_enabled:
        print("LangSmith tracing is disabled. Set LANGCHAIN_TRACING_V2=true to enable.")
        return False

    if not api_key:
        print("LangSmith tracing is enabled but LANGCHAIN_API_KEY is missing.")
        return False

    print(f"LangSmith tracing enabled for project: {os.environ['LANGCHAIN_PROJECT']}")
    return True


def make_run_config(
    state: RecipeState,
    run_name: str = "meal-planner",
    run_id: str | None = None,
) -> dict:
    """Build LangGraph/LangSmith run config with useful metadata."""
    return {
        "run_name": run_name,
        "run_id": run_id or str(uuid.uuid4()),
        "tags": ["meal-planner"],
        "metadata": {
            "ingredients": state["ingredients"],
            "iteration": state.get("iteration", 0),
        },
    }
