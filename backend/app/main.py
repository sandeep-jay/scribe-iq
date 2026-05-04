from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import asyncpg
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import chat as chat_routes
from app.api import note_generate as note_generate_routes
from app.api import notes as notes_routes
from app.api import patients as patient_routes
from app.config import cors_origin_list, get_settings
from app.middleware import OptionalApiKeyMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    settings = get_settings()
    pool = await asyncpg.create_pool(settings.database_url)
    app.state.db_pool = pool
    try:
        yield
    finally:
        await pool.close()


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(title=settings.app_name, lifespan=lifespan)

    application.add_middleware(OptionalApiKeyMiddleware)

    application.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origin_list(settings.cors_origins),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @application.get("/health")
    async def health() -> dict:
        key_set = bool((settings.backend_api_key or "").strip())
        return {
            "status": "ok",
            "service": settings.app_name,
            "llm_provider": settings.llm_provider,
            "note_generation_enabled": settings.note_generation_enabled,
            "meeting_prep_enabled": settings.meeting_prep_enabled,
            "api_auth_configured": key_set,
        }

    application.include_router(patient_routes.router)
    application.include_router(chat_routes.router)
    application.include_router(note_generate_routes.router)
    application.include_router(notes_routes.router)
    return application


app = create_app()
