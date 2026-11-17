"""Punto de entrada: crea la aplicación FastAPI."""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Optional

from pathlib import Path

from fastapi import FastAPI, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse

from . import VERSION
from .config import Settings
from .container import Container
from .domain import NotFoundError, ValidationError
from .metrics import MetricsMiddleware
from .routers import health, orders, products, reports


def create_app(container: Optional[Container] = None) -> FastAPI:
    """Si se pasa un contenedor (tests), se usa tal cual; si no, se construye desde el entorno."""

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        c = container or Container.from_settings(Settings.from_env())
        c.start()
        app.state.container = c
        yield
        c.close()

    app = FastAPI(
        title="Tienda API",
        version=VERSION,
        description="API REST usada para analizar el comportamiento bajo distintos escenarios de despliegue.",
        lifespan=lifespan,
    )
    app.add_middleware(MetricsMiddleware)

    @app.exception_handler(NotFoundError)
    async def not_found_handler(_: Request, exc: NotFoundError):
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(ValidationError)
    async def validation_handler(_: Request, exc: ValidationError):
        return JSONResponse(status_code=422, content={"detail": str(exc)})

    static_index = Path(__file__).parent / "static" / "index.html"

    @app.get("/", include_in_schema=False)
    async def get_index():
        if static_index.exists():
            return HTMLResponse(content=static_index.read_text(encoding="utf-8"))
        return JSONResponse({"status": "ok", "version": VERSION})

    @app.get("/favicon.ico", include_in_schema=False)
    async def get_favicon():
        svg = "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>⚡</text></svg>"
        return Response(content=svg, media_type="image/svg+xml")

    for module in (health, products, orders, reports):
        app.include_router(module.router)
    return app


app = create_app()
