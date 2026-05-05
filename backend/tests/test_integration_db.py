from __future__ import annotations

import pytest


@pytest.mark.integration
@pytest.mark.asyncio
async def test_postgres_connection_works(pg_conn):
    value = await pg_conn.fetchval("SELECT 1")
    assert value == 1
