from dataclasses import asdict
from typing import List, Optional

from fastapi import APIRouter, Query, Request

from ..schemas import ProductOut, ProductPageOut

router = APIRouter(prefix="/products", tags=["productos"])


@router.get("", response_model=ProductPageOut)
def list_products(
    request: Request,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    category_id: Optional[int] = Query(None, ge=1),
):
    return asdict(request.app.state.container.products.list(page, size, category_id))


# Debe declararse antes de /{product_id} para que "search" no se interprete como id.
@router.get("/search", response_model=List[ProductOut])
def search_products(request: Request, q: str = Query(..., min_length=2), limit: int = Query(20, ge=1, le=100)):
    return [asdict(p) for p in request.app.state.container.products.search(q, limit)]


@router.get("/{product_id}", response_model=ProductOut)
def get_product(request: Request, product_id: int):
    return asdict(request.app.state.container.products.get(product_id))
