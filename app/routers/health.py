from fastapi import APIRouter, HTTPException, Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from .. import VERSION
from ..metrics import HOSTNAME

router = APIRouter(tags=["operación"])


@router.get("/health")
async def health():
    """Liveness: no toca la BD ni el threadpool, responde incluso bajo saturación."""
    return {"status": "ok", "pod": HOSTNAME}


@router.get("/ready")
def ready(request: Request):
    """Readiness: comprueba la conexión a PostgreSQL."""
    if not request.app.state.container.is_ready():
        raise HTTPException(status_code=503, detail="base de datos no disponible")
    return {"status": "ready", "pod": HOSTNAME}


@router.get("/info")
async def info():
    """Útil para comprobar qué réplica atendió la petición."""
    return {"app": "tienda-api", "version": VERSION, "pod": HOSTNAME}


@router.get("/metrics", include_in_schema=False)
async def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
