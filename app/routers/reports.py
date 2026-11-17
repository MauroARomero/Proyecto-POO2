from dataclasses import asdict
from typing import List

from fastapi import APIRouter, Query, Request

from ..schemas import CategorySalesOut, DatasetCountsOut, TopProductOut

router = APIRouter(prefix="/reports", tags=["reportes"])


@router.get("/top-products", response_model=List[TopProductOut])
def top_products(request: Request, limit: int = Query(10, ge=1, le=100)):
    """Agregación pesada (JOIN + GROUP BY sobre order_items)."""
    return [asdict(r) for r in request.app.state.container.reports.top_products(limit)]


@router.get("/sales-by-category", response_model=List[CategorySalesOut])
def sales_by_category(request: Request):
    return [asdict(r) for r in request.app.state.container.reports.sales_by_category()]


@router.get("/counts", response_model=DatasetCountsOut)
def counts(request: Request):
    """Cantidad de registros por tabla: sirve para comprobar el mínimo de 10K."""
    return asdict(request.app.state.container.reports.counts())
