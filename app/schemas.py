"""Esquemas Pydantic (contrato JSON de la API REST)."""
from __future__ import annotations

from datetime import datetime
from typing import List

from pydantic import BaseModel, Field


class ProductOut(BaseModel):
    id: int
    sku: str
    name: str
    description: str
    category_id: int
    category: str
    price: float
    stock: int


class ProductPageOut(BaseModel):
    items: List[ProductOut]
    page: int
    size: int
    total: int
    pages: int


class OrderItemIn(BaseModel):
    product_id: int = Field(gt=0)
    quantity: int = Field(ge=1, le=100)


class OrderCreate(BaseModel):
    customer_id: int = Field(gt=0)
    items: List[OrderItemIn] = Field(min_length=1, max_length=50)


class OrderItemOut(BaseModel):
    product_id: int
    quantity: int
    unit_price: float


class OrderOut(BaseModel):
    id: int
    customer_id: int
    status: str
    total: float
    created_at: datetime
    items: List[OrderItemOut]


class TopProductOut(BaseModel):
    product_id: int
    name: str
    category: str
    units_sold: int
    revenue: float


class CategorySalesOut(BaseModel):
    category: str
    orders: int
    units_sold: int
    revenue: float


class DatasetCountsOut(BaseModel):
    categories: int
    products: int
    customers: int
    orders: int
    order_items: int
    total: int
