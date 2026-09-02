import asyncio
import uuid

import streamlit as st

from app import get_thread_state, make_initial_state, run_meal_planner
from models.recipe import Recipe
from utils.messages import OUT_OF_CONTEXT_MESSAGE

st.set_page_config(
    page_title="NutriBot",
    page_icon="🍳",
    layout="wide",
)

if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())


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

    if st.button("New session", use_container_width=True):
        st.session_state.thread_id = str(uuid.uuid4())
        st.session_state.pop("last_result", None)
        st.rerun()

    if st.button("Load saved state", use_container_width=True):
        with st.spinner("Loading..."):
            saved = asyncio.run(get_thread_state(st.session_state.thread_id))
        if saved:
            st.session_state.last_result = saved
            st.success("Loaded persisted state.")
        else:
            st.info("No saved state for this thread yet.")

    st.divider()
    st.markdown(
        "**How it works**\n"
        "1. Validator checks your ingredients\n"
        "2. Chef drafts a recipe\n"
        "3. Inspector checks safety\n"
        "4. Unsafe recipes loop back to Chef (max 3 tries)"
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
            except Exception as exc:
                st.error(f"Something went wrong: {exc}")

if "last_result" in st.session_state:
    st.divider()
    render_result(st.session_state.last_result)
