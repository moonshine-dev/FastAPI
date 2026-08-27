import pytest

pytestmark = pytest.mark.orders


class TestBorrow:
    def test_borrow_success_and_stock_decrement(self, client, created_user, created_book):
        payload = {
            "user_id": created_user["user"]["id"],
            "book_id": created_book["book"]["id"],
            "return_deadline": "2099-01-01T00:00:00",
        }
        resp = client.post("/orders/borrow", json=payload)
        assert resp.status_code == 200
        body = resp.json()
        assert body["user_id"] == payload["user_id"]
        assert body["book_id"] == payload["book_id"]
        assert body["delivery_date"] is None

        # stock must have been decremented by one
        book = client.get("/books/").json()[0]
        assert book["stock"] == created_book["book"]["stock"] - 1

    def test_borrow_nonexistent_book_400(self, client, created_user):
        payload = {
            "user_id": created_user["user"]["id"],
            "book_id": 99999,
            "return_deadline": "2099-01-01T00:00:00",
        }
        resp = client.post("/orders/borrow", json=payload)
        assert resp.status_code == 400
        assert "not found" in resp.json()["detail"].lower()

    def test_borrow_out_of_stock_400(self, client, created_user):
        # create a book with zero stock
        r = client.post(
            "/books/",
            json={"title": "Empty", "author": "A", "price": 5.0, "stock": 0},
        )
        book_id = r.json()["id"]
        payload = {
            "user_id": created_user["user"]["id"],
            "book_id": book_id,
            "return_deadline": "2099-01-01T00:00:00",
        }
        resp = client.post("/orders/borrow", json=payload)
        assert resp.status_code == 400

    def test_borrow_missing_fields_422(self, client):
        resp = client.post("/orders/borrow", json={"user_id": 1})
        assert resp.status_code == 422


class TestReturnBook:
    def test_return_success_restores_stock(self, client, created_order, created_book):
        oid = created_order["order"]["id"]
        original_stock = created_book["book"]["stock"]

        resp = client.put(f"/orders/{oid}/return")
        assert resp.status_code == 200
        body = resp.json()
        assert body["delivery_date"] is not None

        # stock must be restored to its original value
        book = next(
            b for b in client.get("/books/").json() if b["id"] == created_book["book"]["id"]
        )
        assert book["stock"] == original_stock

    def test_double_return_rejected(self, client, created_order):
        oid = created_order["order"]["id"]
        assert client.put(f"/orders/{oid}/return").status_code == 200
        resp = client.put(f"/orders/{oid}/return")
        assert resp.status_code == 400
        assert "already been returned" in resp.json()["detail"]

    def test_return_missing_order_400(self, client):
        resp = client.put("/orders/99999/return")
        assert resp.status_code == 400


class TestDelayedOrders:
    def test_no_delayed_orders_initially(self, client):
        resp = client.get("/orders/delayed")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_overdue_order_appears_in_delayed_list(self, client, created_user, created_book):
        # create an order with a past deadline
        payload = {
            "user_id": created_user["user"]["id"],
            "book_id": created_book["book"]["id"],
            "return_deadline": "2000-01-01T00:00:00",
        }
        r = client.post("/orders/borrow", json=payload)
        assert r.status_code == 200

        resp = client.get("/orders/delayed")
        assert resp.status_code == 200
        ids = [o["id"] for o in resp.json()]
        assert r.json()["id"] in ids


class TestFullWorkflow:
    """Full end-to-end scenario: register -> add book -> borrow -> return."""

    def test_full_lifecycle(self, client):
        # 1. Register a user
        u = client.post(
            "/users/",
            json={"username": "workflow_user", "email": "wf@example.com", "password": "pass123"},
        ).json()

        # 2. Add a book with 2 copies
        b = client.post(
            "/books/",
            json={"title": "Lifecycle", "author": "QA", "price": 10.0, "stock": 2},
        ).json()

        # 3. Borrow twice
        deadline = "2099-06-01T00:00:00"
        o1 = client.post(
            "/orders/borrow",
            json={"user_id": u["id"], "book_id": b["id"], "return_deadline": deadline},
        ).json()
        o2 = client.post(
            "/orders/borrow",
            json={"user_id": u["id"], "book_id": b["id"], "return_deadline": deadline},
        ).json()

        # 4. The third borrow must fail because stock is exhausted
        r3 = client.post(
            "/orders/borrow",
            json={"user_id": u["id"], "book_id": b["id"], "return_deadline": deadline},
        )
        assert r3.status_code == 400

        # 5. Returning one order -> stock becomes 1 again
        client.put(f"/orders/{o1['id']}/return")
        book = next(bk for bk in client.get("/books/").json() if bk["id"] == b["id"])
        assert book["stock"] == 1

        # 6. Borrowing again succeeds
        r4 = client.post(
            "/orders/borrow",
            json={"user_id": u["id"], "book_id": b["id"], "return_deadline": deadline},
        )
        assert r4.status_code == 200
        assert r4.json()["id"] != o2["id"]
