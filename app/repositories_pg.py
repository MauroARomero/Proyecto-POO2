"""Implementación de los repositorios sobre PostgreSQL."""
from __future__ import annotations

from typing import Dict, List, Optional, Sequence

from .database import Database
from .domain import (
    CategorySales,
    DatasetCounts,
    Order,
    OrderLine,
    Product,
    TopProduct,
)
from .ports import CustomerRepository, OrderRepository, ProductRepository, ReportRepository

_PRODUCT_COLUMNS = """
    p.id, p.sku, p.name, p.description, p.category_id,
    c.name AS category, p.price::float8 AS price, p.stock
"""


def _product(row: dict) -> Product:
    return Product(**row)


class PgProductRepository(ProductRepository):
    def __init__(self, db: Database) -> None:
        self._db = db

    def get_by_id(self, product_id: int) -> Optional[Product]:
        with self._db.connection() as conn:
            row = conn.execute(
                f"SELECT {_PRODUCT_COLUMNS} FROM products p "
                "JOIN categories c ON c.id = p.category_id WHERE p.id = %s",
                (product_id,),
            ).fetchone()
        return _product(row) if row else None

    def list(self, limit: int, offset: int, category_id: Optional[int]) -> List[Product]:
        base = f"SELECT {_PRODUCT_COLUMNS} FROM products p JOIN categories c ON c.id = p.category_id"
        with self._db.connection() as conn:
            if category_id is None:
                rows = conn.execute(
                    base + " ORDER BY p.id LIMIT %s OFFSET %s", (limit, offset)
                ).fetchall()
            else:
                rows = conn.execute(
                    base + " WHERE p.category_id = %s ORDER BY p.id LIMIT %s OFFSET %s",
                    (category_id, limit, offset),
                ).fetchall()
        return [_product(r) for r in rows]

    def count(self, category_id: Optional[int]) -> int:
        with self._db.connection() as conn:
            if category_id is None:
                row = conn.execute("SELECT count(*) AS n FROM products").fetchone()
            else:
                row = conn.execute(
                    "SELECT count(*) AS n FROM products WHERE category_id = %s", (category_id,)
                ).fetchone()
        return int(row["n"])

    def search(self, term: str, limit: int) -> List[Product]:
        # Sin índice sobre name: es una búsqueda secuencial a propósito (carga para la BD).
        escaped = term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        with self._db.connection() as conn:
            rows = conn.execute(
                f"SELECT {_PRODUCT_COLUMNS} FROM products p "
                "JOIN categories c ON c.id = p.category_id "
                "WHERE p.name ILIKE %s ORDER BY p.id LIMIT %s",
                (f"%{escaped}%", limit),
            ).fetchall()
        return [_product(r) for r in rows]

    def prices_for(self, product_ids: Sequence[int]) -> Dict[int, float]:
        with self._db.connection() as conn:
            rows = conn.execute(
                "SELECT id, price::float8 AS price FROM products WHERE id = ANY(%s)",
                (list(product_ids),),
            ).fetchall()
        return {r["id"]: r["price"] for r in rows}


class PgCustomerRepository(CustomerRepository):
    def __init__(self, db: Database) -> None:
        self._db = db

    def exists(self, customer_id: int) -> bool:
        with self._db.connection() as conn:
            row = conn.execute(
                "SELECT 1 AS ok FROM customers WHERE id = %s", (customer_id,)
            ).fetchone()
        return row is not None


class PgOrderRepository(OrderRepository):
    def __init__(self, db: Database) -> None:
        self._db = db

    def add(self, customer_id: int, lines: Sequence[OrderLine], total: float) -> Order:
        # Una única transacción: pedido + líneas (escritura representativa para la prueba).
        with self._db.connection() as conn:
            head = conn.execute(
                "INSERT INTO orders (customer_id, status, total) VALUES (%s, 'PENDING', %s) "
                "RETURNING id, created_at",
                (customer_id, total),
            ).fetchone()
            with conn.cursor() as cur:
                cur.executemany(
                    "INSERT INTO order_items (order_id, product_id, quantity, unit_price) "
                    "VALUES (%s, %s, %s, %s)",
                    [(head["id"], l.product_id, l.quantity, l.unit_price) for l in lines],
                )
        return Order(
            id=head["id"],
            customer_id=customer_id,
            status="PENDING",
            total=total,
            created_at=head["created_at"],
            items=list(lines),
        )

    def _items(self, conn, order_id: int) -> List[OrderLine]:
        rows = conn.execute(
            "SELECT product_id, quantity, unit_price::float8 AS unit_price "
            "FROM order_items WHERE order_id = %s ORDER BY id",
            (order_id,),
        ).fetchall()
        return [OrderLine(**r) for r in rows]

    def get_by_id(self, order_id: int) -> Optional[Order]:
        with self._db.connection() as conn:
            row = conn.execute(
                "SELECT id, customer_id, status, total::float8 AS total, created_at "
                "FROM orders WHERE id = %s",
                (order_id,),
            ).fetchone()
            if row is None:
                return None
            return Order(**row, items=self._items(conn, order_id))

    def list_by_customer(self, customer_id: int, limit: int) -> List[Order]:
        with self._db.connection() as conn:
            rows = conn.execute(
                "SELECT id, customer_id, status, total::float8 AS total, created_at "
                "FROM orders WHERE customer_id = %s ORDER BY id DESC LIMIT %s",
                (customer_id, limit),
            ).fetchall()
            return [Order(**r, items=self._items(conn, r["id"])) for r in rows]


class PgReportRepository(ReportRepository):
    def __init__(self, db: Database) -> None:
        self._db = db

    def top_products(self, limit: int) -> List[TopProduct]:
        # Agregación sobre ~90 mil líneas de pedido: consulta intencionalmente pesada.
        with self._db.connection() as conn:
            rows = conn.execute(
                "SELECT p.id AS product_id, p.name, c.name AS category, "
                "       SUM(oi.quantity)::int AS units_sold, "
                "       SUM(oi.quantity * oi.unit_price)::float8 AS revenue "
                "FROM order_items oi "
                "JOIN products p ON p.id = oi.product_id "
                "JOIN categories c ON c.id = p.category_id "
                "GROUP BY p.id, p.name, c.name "
                "ORDER BY revenue DESC LIMIT %s",
                (limit,),
            ).fetchall()
        return [TopProduct(**r) for r in rows]

    def sales_by_category(self) -> List[CategorySales]:
        with self._db.connection() as conn:
            rows = conn.execute(
                "SELECT c.name AS category, "
                "       COUNT(DISTINCT oi.order_id)::int AS orders, "
                "       SUM(oi.quantity)::int AS units_sold, "
                "       SUM(oi.quantity * oi.unit_price)::float8 AS revenue "
                "FROM order_items oi "
                "JOIN products p ON p.id = oi.product_id "
                "JOIN categories c ON c.id = p.category_id "
                "GROUP BY c.name ORDER BY revenue DESC"
            ).fetchall()
        return [CategorySales(**r) for r in rows]

    def counts(self) -> DatasetCounts:
        with self._db.connection() as conn:
            row = conn.execute(
                "SELECT (SELECT count(*) FROM categories)  AS categories, "
                "       (SELECT count(*) FROM products)    AS products, "
                "       (SELECT count(*) FROM customers)   AS customers, "
                "       (SELECT count(*) FROM orders)      AS orders, "
                "       (SELECT count(*) FROM order_items) AS order_items"
            ).fetchone()
        total = sum(row.values())
        return DatasetCounts(**row, total=total)
