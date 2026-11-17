from dataclasses import asdict
from typing import List

from fastapi import APIRouter, Query, Request

from ..domain import OrderLine
from ..schemas import OrderCreate, OrderOut

router = APIRouter(tags=["pedidos"])


@router.post("/orders", response_model=OrderOut, status_code=201)
def create_order(request: Request, body: OrderCreate):
    lines = [OrderLine(i.product_id, i.quantity) for i in body.items]
    order = request.app.state.container.orders.place_order(body.customer_id, lines)
    return asdict(order)


@router.get("/orders/{order_id}", response_model=OrderOut)
def get_order(request: Request, order_id: int):
    return asdict(request.app.state.container.orders.get(order_id))


@router.get("/customers/{customer_id}/orders", response_model=List[OrderOut])
def list_customer_orders(request: Request, customer_id: int, limit: int = Query(20, ge=1, le=100)):
    orders = request.app.state.container.orders.list_for_customer(customer_id, limit)
    return [asdict(o) for o in orders]
