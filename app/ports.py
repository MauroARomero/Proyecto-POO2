"""Puertos (interfaces) de persistencia.

Los servicios dependen de estas abstracciones, no de PostgreSQL (principio de
inversión de dependencias). Así se pueden probar con repositorios en memoria.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Sequence

from .domain import (
    CategorySales,
    DatasetCounts,
    Order,
    OrderLine,
    Product,
    TopProduct,
)


class ProductRepository(ABC):
    @abstractmethod
    def get_by_id(self, product_id: int) -> Optional[Product]: ...

    @abstractmethod
    def list(self, limit: int, offset: int, category_id: Optional[int]) -> List[Product]: ...

    @abstractmethod
    def count(self, category_id: Optional[int]) -> int: ...

    @abstractmethod
    def search(self, term: str, limit: int) -> List[Product]: ...

    @abstractmethod
    def prices_for(self, product_ids: Sequence[int]) -> Dict[int, float]: ...


class CustomerRepository(ABC):
    @abstractmethod
    def exists(self, customer_id: int) -> bool: ...


class OrderRepository(ABC):
    @abstractmethod
    def add(self, customer_id: int, lines: Sequence[OrderLine], total: float) -> Order: ...

    @abstractmethod
    def get_by_id(self, order_id: int) -> Optional[Order]: ...

    @abstractmethod
    def list_by_customer(self, customer_id: int, limit: int) -> List[Order]: ...


class ReportRepository(ABC):
    @abstractmethod
    def top_products(self, limit: int) -> List[TopProduct]: ...

    @abstractmethod
    def sales_by_category(self) -> List[CategorySales]: ...

    @abstractmethod
    def counts(self) -> DatasetCounts: ...
