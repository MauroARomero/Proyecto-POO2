"""Raíz de composición: construye y conecta repositorios y servicios."""
from __future__ import annotations

from typing import Optional

from .config import Settings
from .ports import CustomerRepository, OrderRepository, ProductRepository, ReportRepository
from .services import OrderService, ProductService, ReportService


class Container:
    def __init__(
        self,
        settings: Settings,
        product_repo: ProductRepository,
        customer_repo: CustomerRepository,
        order_repo: OrderRepository,
        report_repo: ReportRepository,
        database=None,
    ) -> None:
        self.settings = settings
        self.database = database
        self.products = ProductService(
            product_repo, settings.default_page_size, settings.max_page_size
        )
        self.orders = OrderService(order_repo, customer_repo, product_repo)
        self.reports = ReportService(report_repo)

    @classmethod
    def from_settings(cls, settings: Settings) -> "Container":
        # Importación diferida: los tests con repositorios falsos no necesitan psycopg.
        from .database import Database
        from .repositories_pg import (
            PgCustomerRepository,
            PgOrderRepository,
            PgProductRepository,
            PgReportRepository,
        )

        db = Database(settings)
        return cls(
            settings,
            PgProductRepository(db),
            PgCustomerRepository(db),
            PgOrderRepository(db),
            PgReportRepository(db),
            database=db,
        )

    def start(self) -> None:
        if self.database is not None:
            self.database.open()

    def is_ready(self) -> bool:
        return self.database.ping() if self.database is not None else True

    def close(self) -> None:
        if self.database is not None:
            self.database.close()
