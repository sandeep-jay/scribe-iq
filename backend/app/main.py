from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import asyncpg
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import chat as chat_routes
from app.api import note_generate as note_generate_routes
from app.api import admin_responsible_ai as admin_responsible_ai_routes
from app.api import notes as notes_routes
from app.api import patients as patient_routes
from app.config import cors_origin_list, get_settings
from app.logging_config import configure_logging
from app.middleware import OptionalApiKeyMiddleware, RequestLoggingMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    settings = get_settings()
    configure_logging(settings)
    try:
        pool = await asyncpg.create_pool(
            settings.database_url,
            min_size=settings.db_pool_min_size,
            max_size=settings.db_pool_max_size,
            command_timeout=settings.db_pool_command_timeout_s,
        )
    except TypeError:
        # Test fakes may monkeypatch create_pool with a minimal signature.
        pool = await asyncpg.create_pool(settings.database_url)
    app.state.db_pool = pool
    try:
        yield
    finally:
        await pool.close()


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(title=settings.app_name, lifespan=lifespan)

    # Starlette runs last-added middleware first on the request path; put CORS outermost,
    # then request logging (so 401 from API key still emits request_completed), then auth.
    application.add_middleware(OptionalApiKeyMiddleware)
    application.add_middleware(RequestLoggingMiddleware)

    relax = settings.cors_relax_local
    allow_origin_regex = (
        r"^https?://(localhost|127\.0\.0\.1):\d+$"
        r"|^https?://192\.168\.\d{1,3}\.\d{1,3}:\d+$"
        if relax
        else None
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origin_list(settings.cors_origins),
        allow_origin_regex=allow_origin_regex,
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
            "llm_provider": settings.normalized_llm_provider(),
            "llm_configured": settings.llm_configured(),
            "llm_json_mode": settings.llm_json_mode_capability(),
            "embedding_provider": settings.embedding_provider,
            "embedding_configured": settings.embedding_configured(),
            "note_generation_enabled": settings.note_generation_enabled,
            "meeting_prep_enabled": settings.meeting_prep_enabled,
            "responsible_ai_admin_enabled": settings.responsible_ai_admin_enabled,
            "api_auth_configured": key_set,
        }

    application.include_router(patient_routes.router)
    application.include_router(chat_routes.router)
    application.include_router(note_generate_routes.router)
    application.include_router(notes_routes.router)
    if settings.responsible_ai_admin_enabled:
        application.include_router(admin_responsible_ai_routes.router)
    return application


app = create_app()
