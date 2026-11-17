"""Repositorios en memoria para probar servicios y API sin PostgreSQL."""
from datetime import datetime, timezone

from app.domain import (
    CategorySales,
    DatasetCounts,
    Order,
    Product,
    TopProduct,
)
from app.ports import CustomerRepository, OrderRepository, ProductRepository, ReportRepository


class FakeProducts(ProductRepository):
    def __init__(self, n=250):
        self.items = {
            i: Product(i, f"SKU-{i:06d}", f"Producto {i}", "desc", 1 + i % 20, f"Categoría {1 + i % 20}", 10.0 + i, 5)
            for i in range(1, n + 1)
        }

    def get_by_id(self, product_id):
        return self.items.get(product_id)

    def _filtered(self, category_id):
        vals = sorted(self.items.values(), key=lambda p: p.id)
        return [p for p in vals if category_id is None or p.category_id == category_id]

    def list(self, limit, offset, category_id):
        return self._filtered(category_id)[offset : offset + limit]

    def count(self, category_id):
        return len(self._filtered(category_id))

    def search(self, term, limit):
        return [p for p in self._filtered(None) if term.lower() in p.name.lower()][:limit]

    def prices_for(self, product_ids):
        return {i: self.items[i].price for i in product_ids if i in self.items}


class FakeCustomers(CustomerRepository):
    def __init__(self, n=100):
        self.ids = set(range(1, n + 1))

    def exists(self, customer_id):
        return customer_id in self.ids


class FakeOrders(OrderRepository):
    def __init__(self):
        self.orders = {}

    def add(self, customer_id, lines, total):
        oid = len(self.orders) + 1
        order = Order(oid, customer_id, "PENDING", total, datetime.now(timezone.utc), list(lines))
        self.orders[oid] = order
        return order

    def get_by_id(self, order_id):
        return self.orders.get(order_id)

    def list_by_customer(self, customer_id, limit):
        return [o for o in self.orders.values() if o.customer_id == customer_id][:limit]


class FakeReports(ReportRepository):
    def top_products(self, limit):
        return [TopProduct(1, "Producto 1", "Categoría 2", 10, 100.0)][:limit]

    def sales_by_category(self):
        return [CategorySales("Categoría 2", 3, 10, 100.0)]

    def counts(self):
        return DatasetCounts(20, 20000, 10000, 30000, 90000, 150020)
