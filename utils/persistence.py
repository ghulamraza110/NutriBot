from contextlib import asynccontextmanager
from pathlib import Path

import aiosqlite
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.graph import StateGraph

CHECKPOINT_DB = str(Path(__file__).resolve().parent.parent / "checkpoints.db")


def _patch_aiosqlite_compat() -> None:
    """aiosqlite 0.22+ removed is_alive(); older langgraph-checkpoint-sqlite still calls it."""
    if not hasattr(aiosqlite.Connection, "is_alive"):
        aiosqlite.Connection.is_alive = lambda self: True  # type: ignore[attr-defined]


_patch_aiosqlite_compat()


@asynccontextmanager
async def compiled_app(workflow: StateGraph):
    async with AsyncSqliteSaver.from_conn_string(CHECKPOINT_DB) as checkpointer:
        yield workflow.compile(checkpointer=checkpointer)
