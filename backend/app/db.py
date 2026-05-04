"""Async Postgres helpers (asyncpg)."""

from __future__ import annotations

from collections.abc import AsyncGenerator

import asyncpg
from fastapi import Request


async def get_conn(request: Request) -> AsyncGenerator[asyncpg.Connection, None]:
    pool: asyncpg.Pool = request.app.state.db_pool
    async with pool.acquire() as conn:
        yield conn
