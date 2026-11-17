"""Servicios: reglas de negocio de la aplicación (sin HTTP ni SQL)."""
from __future__ import annotations

import math
from typing import Dict, List, Optional, Sequence

from .domain import (
    CategorySales,
    DatasetCounts,
    NotFoundError,
    Order,
    OrderLine,
    Product,
    ProductPage,
    TopProduct,
    ValidationError,
)
from .ports import CustomerRepository, OrderRepository, ProductRepository, ReportRepository


class ProductService:
    def __init__(
        self,
        products: ProductRepository,
        default_page_size: int = 20,
        max_page_size: int = 100,
    ) -> None:
        self._products = products
        self._default_size = default_page_size
        self._max_size = max_page_size

    def get(self, product_id: int) -> Product:
        product = self._products.get_by_id(product_id)
        if product is None:
            raise NotFoundError(f"Producto {product_id} no existe")
        return product

    def list(
        self,
        page: int = 1,
        size: Optional[int] = None,
        category_id: Optional[int] = None,
    ) -> ProductPage:
        if page < 1:
            raise ValidationError("page debe ser >= 1")
        size = min(size or self._default_size, self._max_size)
        if size < 1:
            raise ValidationError("size debe ser >= 1")
        total = self._products.count(category_id)
        items = self._products.list(size, (page - 1) * size, category_id)
        pages = math.ceil(total / size) if total else 0
        return ProductPage(items=items, page=page, size=size, total=total, pages=pages)

    def search(self, term: str, limit: int = 20) -> List[Product]:
        term = (term or "").strip()
        if len(term) < 2:
            raise ValidationError("El término de búsqueda debe tener al menos 2 caracteres")
        return self._products.search(term, min(max(limit, 1), self._max_size))


class OrderService:
    MAX_LINES = 50

    def __init__(
        self,
        orders: OrderRepository,
        customers: CustomerRepository,
        products: ProductRepository,
    ) -> None:
        self._orders = orders
        self._customers = customers
        self._products = products

    def place_order(self, customer_id: int, lines: Sequence[OrderLine]) -> Order:
        if not lines:
            raise ValidationError("El pedido debe tener al menos una línea")
        if len(lines) > self.MAX_LINES:
            raise ValidationError(f"Máximo {self.MAX_LINES} líneas por pedido")

        # Unifica líneas repetidas del mismo producto.
        quantities: Dict[int, int] = {}
        for line in lines:
            if line.quantity < 1:
                raise ValidationError("La cantidad debe ser >= 1")
            quantities[line.product_id] = quantities.get(line.product_id, 0) + line.quantity

        if not self._customers.exists(customer_id):
            raise NotFoundError(f"Cliente {customer_id} no existe")

        prices = self._products.prices_for(list(quantities))
        missing = sorted(set(quantities) - set(prices))
        if missing:
            raise NotFoundError(f"Productos inexistentes: {missing}")

        priced = [OrderLine(pid, qty, prices[pid]) for pid, qty in quantities.items()]
        total = round(sum(l.quantity * l.unit_price for l in priced), 2)
        return self._orders.add(customer_id, priced, total)

    def get(self, order_id: int) -> Order:
        order = self._orders.get_by_id(order_id)
        if order is None:
            raise NotFoundError(f"Pedido {order_id} no existe")
        return order

    def list_for_customer(self, customer_id: int, limit: int = 20) -> List[Order]:
        return self._orders.list_by_customer(customer_id, min(max(limit, 1), 100))


class ReportService:
    def __init__(self, reports: ReportRepository) -> None:
        self._reports = reports

    def top_products(self, limit: int = 10) -> List[TopProduct]:
        return self._reports.top_products(min(max(limit, 1), 100))

    def sales_by_category(self) -> List[CategorySales]:
        return self._reports.sales_by_category()

    def counts(self) -> DatasetCounts:
        return self._reports.counts()
