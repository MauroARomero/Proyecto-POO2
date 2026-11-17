"""Pruebas unitarias de la lógica de negocio (no requieren BD ni FastAPI)."""
import unittest

from app.domain import NotFoundError, OrderLine, ValidationError
from app.services import OrderService, ProductService, ReportService
from tests.fakes import FakeCustomers, FakeOrders, FakeProducts, FakeReports


class ProductServiceTest(unittest.TestCase):
    def setUp(self):
        self.svc = ProductService(FakeProducts(250), default_page_size=20, max_page_size=100)

    def test_get_existing(self):
        self.assertEqual(self.svc.get(5).id, 5)

    def test_get_missing_raises(self):
        with self.assertRaises(NotFoundError):
            self.svc.get(9999)

    def test_pagination(self):
        page = self.svc.list(page=3, size=100)
        self.assertEqual((page.total, page.pages, len(page.items)), (250, 3, 50))
        self.assertEqual(page.items[0].id, 201)

    def test_size_is_capped(self):
        self.assertEqual(self.svc.list(size=5000).size, 100)

    def test_invalid_page(self):
        with self.assertRaises(ValidationError):
            self.svc.list(page=0)

    def test_filter_by_category(self):
        page = self.svc.list(category_id=3, size=100)
        self.assertTrue(all(p.category_id == 3 for p in page.items))

    def test_search_requires_two_chars(self):
        with self.assertRaises(ValidationError):
            self.svc.search("a")
        self.assertTrue(self.svc.search("Producto 1"))


class OrderServiceTest(unittest.TestCase):
    def setUp(self):
        self.products = FakeProducts(50)
        self.svc = OrderService(FakeOrders(), FakeCustomers(10), self.products)

    def test_place_order_computes_total_and_merges_lines(self):
        order = self.svc.place_order(1, [OrderLine(1, 2), OrderLine(1, 1), OrderLine(2, 1)])
        self.assertEqual(len(order.items), 2)
        expected = 3 * self.products.items[1].price + self.products.items[2].price
        self.assertAlmostEqual(order.total, expected)
        self.assertEqual(self.svc.get(order.id).customer_id, 1)

    def test_unknown_customer(self):
        with self.assertRaises(NotFoundError):
            self.svc.place_order(999, [OrderLine(1, 1)])

    def test_unknown_product(self):
        with self.assertRaises(NotFoundError):
            self.svc.place_order(1, [OrderLine(9999, 1)])

    def test_empty_order(self):
        with self.assertRaises(ValidationError):
            self.svc.place_order(1, [])

    def test_bad_quantity(self):
        with self.assertRaises(ValidationError):
            self.svc.place_order(1, [OrderLine(1, 0)])

    def test_list_for_customer(self):
        self.svc.place_order(2, [OrderLine(1, 1)])
        self.assertEqual(len(self.svc.list_for_customer(2)), 1)


class ReportServiceTest(unittest.TestCase):
    def test_counts_meet_minimum_dataset(self):
        counts = ReportService(FakeReports()).counts()
        self.assertGreaterEqual(counts.total, 10_000)


if __name__ == "__main__":
    unittest.main()
