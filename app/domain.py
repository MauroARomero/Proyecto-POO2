"""Modelo de dominio: entidades inmutables y errores de negocio.

No dependen de FastAPI ni de PostgreSQL, por lo que se pueden probar de forma aislada.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import List


# ----------------------------------------------------------------- errores
class DomainError(Exception):
    """Error base de la lógica de negocio."""


class NotFoundError(DomainError):
    """El recurso solicitado no existe."""


class ValidationError(DomainError):
    """La petición no cumple una regla de negocio."""


# --------------------------------------------------------------- entidades
@dataclass(frozen=True)
class Product:
    id: int
    sku: str
    name: str
    description: str
    category_id: int
    category: str
    price: float
    stock: int


@dataclass(frozen=True)
class ProductPage:
    items: List[Product]
    page: int
    size: int
    total: int
    pages: int


@dataclass(frozen=True)
class OrderLine:
    product_id: int
    quantity: int
    unit_price: float = 0.0


@dataclass(frozen=True)
class Order:
    id: int
    customer_id: int
    status: str
    total: float
    created_at: datetime
    items: List[OrderLine] = field(default_factory=list)


@dataclass(frozen=True)
class TopProduct:
    product_id: int
    name: str
    category: str
    units_sold: int
    revenue: float


@dataclass(frozen=True)
class CategorySales:
    category: str
    orders: int
    units_sold: int
    revenue: float


@dataclass(frozen=True)
class DatasetCounts:
    categories: int
    products: int
    customers: int
    orders: int
    order_items: int
    total: int
