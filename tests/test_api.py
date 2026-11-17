"""Pruebas de la API HTTP con repositorios falsos (requieren fastapi y httpx instalados)."""
import unittest

try:
    from fastapi.testclient import TestClient
    HAVE_FASTAPI = True
except Exception:  # fastapi/httpx no instalados
    HAVE_FASTAPI = False

if HAVE_FASTAPI:
    from app.config import Settings
    from app.container import Container
    from app.main import create_app
    from tests.fakes import FakeCustomers, FakeOrders, FakeProducts, FakeReports


@unittest.skipUnless(HAVE_FASTAPI, "fastapi/httpx no están instalados")
class ApiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        container = Container(Settings(), FakeProducts(250), FakeCustomers(10), FakeOrders(), FakeReports())
        cls.client = TestClient(create_app(container))
        cls.client.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.client.__exit__(None, None, None)

    def test_health_and_served_by_header(self):
        r = self.client.get("/health")
        self.assertEqual(r.status_code, 200)
        self.assertIn("x-served-by", r.headers)

    def test_list_and_get_product(self):
        r = self.client.get("/products", params={"page": 2, "size": 10})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["items"][0]["id"], 11)
        self.assertEqual(self.client.get("/products/7").json()["id"], 7)
        self.assertEqual(self.client.get("/products/99999").status_code, 404)

    def test_search_route_is_not_shadowed_by_id_route(self):
        r = self.client.get("/products/search", params={"q": "Producto 1"})
        self.assertEqual(r.status_code, 200)
        self.assertIsInstance(r.json(), list)

    def test_create_order(self):
        body = {"customer_id": 1, "items": [{"product_id": 1, "quantity": 2}]}
        r = self.client.post("/orders", json=body)
        self.assertEqual(r.status_code, 201)
        oid = r.json()["id"]
        self.assertEqual(self.client.get(f"/orders/{oid}").status_code, 200)
        bad = self.client.post("/orders", json={"customer_id": 1, "items": []})
        self.assertEqual(bad.status_code, 422)

    def test_reports_and_metrics(self):
        self.assertEqual(self.client.get("/reports/counts").json()["total"], 150020)
        self.assertEqual(self.client.get("/reports/top-products").status_code, 200)
        self.assertIn("http_requests_total", self.client.get("/metrics").text)


if __name__ == "__main__":
    unittest.main()
