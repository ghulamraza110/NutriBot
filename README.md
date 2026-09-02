# NutriBot — Automated Meal & Recipe Planner

An AI-powered meal planner built with **LangGraph**, **LangChain**, and **Streamlit**. Users enter ingredients they have on hand; the system validates the input, generates a recipe, and inspects it for safety — looping back to revise unsafe drafts up to 3 times.

## Features

- **LangGraph workflow** — Validator → Chef → Inspector with conditional retry loop
- **Structured outputs** — Pydantic models for recipes and inspector results
- **Input validation** — blocks harmful, non-food, and out-of-context requests
- **Async execution** — non-blocking LLM calls with `ainvoke`
- **LangSmith tracing** — optional observability for every node decision
- **SQLite persistence** — conversation state saved per thread ID
- **Streamlit UI** — interactive web frontend with inspector feedback

## How It Works

```
START
  │
  ▼
┌─────────────┐
│  Validator  │─── invalid / out-of-context ──► END
└─────────────┘
  │ valid
  ▼
┌─────────────┐
│    Chef     │  generates structured Recipe (title, steps, cook time, servings)
└─────────────┘
  │
  ▼
┌─────────────┐
│  Inspector  │─── safe ──────────────────────► END (serve)
└─────────────┘
  │ unsafe & iteration < 3
  └──────────────────────────────────────────► Chef (recook)
  │ unsafe & iteration ≥ 3
  └──────────────────────────────────────────► END (stop)
```

### Nodes

| Node | Role |
|------|------|
| **Validator** | Rule-based checks before any LLM call — harmful items, spoiled food, weapons, allergies, out-of-context requests |
| **Chef** | Drafts a structured recipe from ingredients (revises using inspector critique on retry) |
| **Inspector** | Evaluates food safety, realism, ingredient match, and allergies |

## Project Structure

```
meal-planner/
├── app.py                  # LangGraph workflow + CLI entry point
├── streamlit_app.py        # Streamlit web UI (NutriBot)
├── requirements.txt
├── models/
│   ├── state.py            # RecipeState TypedDict
│   ├── recipe.py           # Recipe Pydantic model
│   └── inspector_result.py # InspectorResult Pydantic model
├── nodes/
│   ├── validator.py        # Input validation & safety rules
│   ├── chef.py             # Recipe generation (structured output)
│   └── inspector.py        # Safety inspection (structured output)
└── utils/
    ├── routing.py          # Conditional edge logic
    ├── tracing.py          # LangSmith setup & run config
    ├── persistence.py      # SQLite checkpointer
    └── messages.py         # Shared user-facing messages
```

## Setup

### 1. Clone and install dependencies

```bash
cd meal-planner
pip install -r requirements.txt
```

### 2. Configure environment variables

Create a `.env` file in the project root:

```env
# LLM (OpenRouter example)
OPENAI_API_KEY=your-openrouter-api-key

# LangSmith tracing (optional)
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=lsv2_your-langsmith-api-key
LANGCHAIN_PROJECT=meal-planner
```

The Chef and Inspector use **OpenRouter** with `gpt-4o-mini` by default. Update the model and `base_url` in `nodes/chef.py` and `nodes/inspector.py` if you use a different provider.

## Usage

### Streamlit UI (recommended)

```bash
streamlit run streamlit_app.py
```

Open the app in your browser (usually `http://localhost:8501`), enter ingredients, and click **Generate recipe**.

The UI shows:
- **Validator** rejection or **Inspector** approval status
- Structured recipe (title, servings, cook time, steps)
- Inspector report with feedback

### CLI

```bash
python app.py
```

Runs a demo with `chicken, rice, onion, tomato` and prints the result to the terminal.

### Programmatic usage

```python
import asyncio
from app import make_initial_state, run_meal_planner, get_thread_state

async def main():
    state = make_initial_state("chicken, rice, onion, tomato")
    result = await run_meal_planner(state, thread_id="my-session")
    print(result)

    saved = await get_thread_state("my-session")
    print(saved)

asyncio.run(main())
```

## Input Validation

The Validator runs **before** the Chef and blocks:

| Category | Examples |
|----------|----------|
| Out of context | weather, homework, code, politics, general questions |
| Weapons / harmful | atom bomb, explosives, weapons |
| Non-food items | medicine, chemicals, detergent |
| Unsafe food | expired, rotten, moldy ingredients |
| Non-edible animals | snake, rat, mamba |
| Allergy conflicts | lists pepper but says "allergic to pepper" |

Out-of-context requests receive:

> I don't have that information. I only have info about recipes and cooking. Please list the food ingredients you have.

## Implementation Phases

| Phase | Status | Description |
|-------|--------|-------------|
| 1 | Done | Core LangGraph workflow (Chef ↔ Inspector loop) |
| 2 | Done | Pydantic structured outputs (`Recipe`, `InspectorResult`) |
| 3 | Done | Input Validator node |
| 4 | Done | Async nodes and `ainvoke` |
| 5 | Done | LangSmith tracing |
| 6 | Done | SQLite checkpointer for thread persistence |
| 7 | Planned | Tools & RAG (ingredient lookup, food safety knowledge base) |
| 8 | Planned | Human-in-the-loop approval for borderline recipes |

## Persistence

Conversation state is stored in `checkpoints.db` (SQLite). Each run uses a `thread_id` so you can resume or inspect prior sessions.

```python
result = await run_meal_planner(state, thread_id="user-123")
saved = await get_thread_state("user-123")
```

In the Streamlit sidebar, use **Load saved state** to retrieve a thread's last state.

## LangSmith Tracing

When `LANGCHAIN_TRACING_V2=true` and `LANGCHAIN_API_KEY` are set, every node execution is traced in [LangSmith](https://smith.langchain.com). You can inspect:

- Why the Inspector rejected a recipe
- How the Chef revised drafts across iterations
- Validator routing decisions

## Tech Stack

- [LangGraph](https://github.com/langchain-ai/langgraph) — agent workflow orchestration
- [LangChain](https://github.com/langchain-ai/langchain) — LLM integration
- [Pydantic](https://docs.pydantic.dev/) — structured output validation
- [Streamlit](https://streamlit.io/) — web UI
- [LangSmith](https://smith.langchain.com/) — optional tracing
- [OpenRouter](https://openrouter.ai/) — LLM API (configurable)

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
