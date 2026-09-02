import asyncio
import uuid

import streamlit as st

from app import get_thread_state, list_saved_threads, make_initial_state, run_meal_planner
from models.recipe import Recipe
from utils.messages import OUT_OF_CONTEXT_MESSAGE

st.set_page_config(
    page_title="NutriBot",
    page_icon="🍳",
    layout="wide",
)


def init_thread_id() -> str:
    """Keep the same thread across page reloads via URL query params."""
    query_thread = st.query_params.get("thread_id")
    if query_thread:
        st.session_state.thread_id = query_thread
        return query_thread

    if "thread_id" not in st.session_state:
        st.session_state.thread_id = str(uuid.uuid4())

    st.query_params["thread_id"] = st.session_state.thread_id
    return st.session_state.thread_id


def set_thread_id(thread_id: str) -> None:
    st.session_state.thread_id = thread_id
    st.query_params["thread_id"] = thread_id


def load_saved_result(thread_id: str) -> bool:
    saved = asyncio.run(get_thread_state(thread_id))
    if not saved:
        return False
    st.session_state.last_result = saved
    return True


thread_id = init_thread_id()

if "hydrated_thread" not in st.session_state:
    if load_saved_result(thread_id):
        st.session_state.hydrated_thread = thread_id
    else:
        st.session_state.hydrated_thread = ""


def render_recipe(recipe_json: str) -> None:
    recipe = Recipe.model_validate_json(recipe_json)
    col1, col2, col3 = st.columns(3)
    col1.metric("Servings", recipe.servings)
    col2.metric("Cook time", f"{recipe.cook_time_minutes} min")
    col3.metric("Steps", len(recipe.steps))

    st.subheader(recipe.title)
    for i, step in enumerate(recipe.steps, start=1):
        st.markdown(f"**{i}.** {step}")


def render_result(result: dict) -> None:
    rejected = bool(result.get("critique")) and not result.get("recipe_proposal")

    status_col, iter_col = st.columns(2)
    with iter_col:
        st.metric("Iterations", result.get("iteration", 0))

    if rejected:
        is_out_of_context = result.get("rejection_type") == "out_of_context"
        with status_col:
            if is_out_of_context:
                st.info("Out of scope")
            else:
                st.error("Validator: Rejected")
        if is_out_of_context:
            st.info(result.get("critique") or OUT_OF_CONTEXT_MESSAGE)
        else:
            st.warning(result["critique"])
        return

    with status_col:
        if result.get("is_safe"):
            st.success("Inspector: Approved")
        else:
            st.error("Inspector: Rejected")

    if not result.get("is_safe"):
        is_out_of_context = result.get("rejection_type") == "out_of_context"
        if is_out_of_context:
            st.info("Out of scope")
            st.info(result.get("critique") or OUT_OF_CONTEXT_MESSAGE)
        else:
            st.error("No safe recipe could be produced")
            with st.expander("Inspector report", expanded=True):
                st.write(result.get("critique") or "The inspector could not approve a safe recipe.")
        return

    if result.get("recipe_proposal"):
        render_recipe(result["recipe_proposal"])

    with st.expander("Inspector report", expanded=bool(result.get("critique"))):
        if result.get("critique"):
            st.write(result["critique"])
        else:
            st.write("Recipe passed all safety checks.")


st.title("🍳 NutriBot")
st.caption("LangGraph workflow: Validator → Chef → Inspector (with retry loop)")

with st.sidebar:
    st.header("Session")
    st.text_input("Thread ID", value=st.session_state.thread_id, disabled=True)

    saved_threads = list_saved_threads()
    if saved_threads:
        selected_thread = st.selectbox(
            "Saved sessions",
            options=saved_threads,
            index=saved_threads.index(st.session_state.thread_id)
            if st.session_state.thread_id in saved_threads
            else 0,
            help="Switch to a previous saved conversation.",
        )
        if st.button("Open saved session", use_container_width=True):
            set_thread_id(selected_thread)
            if load_saved_result(selected_thread):
                st.session_state.hydrated_thread = selected_thread
                st.success("Loaded saved session.")
                st.rerun()
            else:
                st.info("No saved state for that thread.")

    if st.button("New session", use_container_width=True):
        set_thread_id(str(uuid.uuid4()))
        st.session_state.pop("last_result", None)
        st.session_state.hydrated_thread = ""
        st.rerun()

    if st.button("Reload saved state", use_container_width=True):
        if load_saved_result(st.session_state.thread_id):
            st.session_state.hydrated_thread = st.session_state.thread_id
            st.success("Loaded persisted state.")
            st.rerun()
        else:
            st.info("No saved state for this thread yet. Generate a recipe first.")

    st.divider()
    st.markdown(
        "**How it works**\n"
        "1. Validator checks your ingredients\n"
        "2. Chef drafts a recipe\n"
        "3. Inspector checks safety\n"
        "4. Unsafe recipes loop back to Chef (max 3 tries)\n\n"
        "**Tip:** Your thread ID stays in the URL, so saved recipes survive page reloads."
    )

ingredients = st.text_area(
    "What's in your kitchen?",
    value="chicken, rice, onion, tomato",
    height=100,
    placeholder="e.g. chicken, rice, onion, tomato",
    help="Only cooking and recipe requests are supported.",
)

col_generate, col_clear = st.columns([1, 4])
with col_generate:
    generate = st.button("Generate recipe", type="primary", use_container_width=True)
with col_clear:
    if st.button("Clear results", use_container_width=True):
        st.session_state.pop("last_result", None)
        st.rerun()

if generate:
    if not ingredients.strip():
        st.error("Please enter at least one ingredient.")
    else:
        with st.spinner("Validator → Chef → Inspector..."):
            try:
                state = make_initial_state(ingredients.strip())
                result = asyncio.run(
                    run_meal_planner(
                        state,
                        thread_id=st.session_state.thread_id,
                        run_name="meal-planner-streamlit",
                    )
                )
                st.session_state.last_result = result
                st.session_state.hydrated_thread = st.session_state.thread_id
            except Exception as exc:
                st.error(f"Something went wrong: {exc}")

if "last_result" in st.session_state:
    st.divider()
    render_result(st.session_state.last_result)
