"""FastAPI entrypoint for the NityaMed Modular Monolith."""

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.core.exceptions import register_exception_handlers
from app.modules.admin.router import admin_router
from app.modules.analytics.router import analytics_router
from app.modules.assistant.router import assistant_router
from app.modules.auth.router import auth_router, profile_router
from app.modules.inventory.router import inventory_router
from app.modules.medicines.router import catalogue_router, medicines_router
from app.modules.notifications.router import internal_router, notifications_router
from app.modules.refill.router import refill_router
from app.modules.schedules.router import doses_router, schedules_router
from app.modules.sync.router import sync_router


def create_app() -> FastAPI:
    """Construct and configure the NityaMed FastAPI application."""
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    register_exception_handlers(app)

    app.include_router(auth_router, prefix=settings.api_v1_prefix)
    app.include_router(profile_router, prefix=settings.api_v1_prefix)
    app.include_router(catalogue_router, prefix=settings.api_v1_prefix)
    app.include_router(medicines_router, prefix=settings.api_v1_prefix)
    app.include_router(schedules_router, prefix=settings.api_v1_prefix)
    app.include_router(doses_router, prefix=settings.api_v1_prefix)
    app.include_router(inventory_router, prefix=settings.api_v1_prefix)
    app.include_router(refill_router, prefix=settings.api_v1_prefix)
    app.include_router(notifications_router, prefix=settings.api_v1_prefix)
    app.include_router(internal_router, prefix=settings.api_v1_prefix)
    app.include_router(sync_router, prefix=settings.api_v1_prefix)
    app.include_router(analytics_router, prefix=settings.api_v1_prefix)
    app.include_router(assistant_router, prefix=settings.api_v1_prefix)
    app.include_router(admin_router, prefix=settings.api_v1_prefix)

    @app.get("/health", tags=["Health"])
    def health_check(db: Session = Depends(get_db)) -> dict[str, str]:
        """Verify API liveness and database connectivity."""
        db.execute(text("SELECT 1"))
        return {"status": "ok", "service": "nityamed-api"}

    return app


app = create_app()
