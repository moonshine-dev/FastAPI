import pytest

pytestmark = pytest.mark.orders


class TestBorrow:
    def test_borrow_success_and_stock_decrement(self, client, created_user, created_book):
        payload = {
            "user_id": created_user["user"]["id"],
            "book_id": created_book["book"]["id"],
            "return_deadline": "2099-01-01T00:00:00",
        }
        resp = client.post("/api/v1/orders/borrow", json=payload)
        assert resp.status_code == 200
        body = resp.json()
        assert body["user_id"] == payload["user_id"]
        assert body["book_id"] == payload["book_id"]
        assert body["delivery_date"] is None

        # stock must have been decremented by one
        book = client.get("/api/v1/books/").json()["items"][0]
        assert book["stock"] == created_book["book"]["stock"] - 1

    def test_borrow_nonexistent_book_400(self, client, created_user):
        payload = {
            "user_id": created_user["user"]["id"],
            "book_id": 99999,
            "return_deadline": "2099-01-01T00:00:00",
        }
        resp = client.post("/api/v1/orders/borrow", json=payload)
        assert resp.status_code == 400
        assert "not found" in resp.json()["detail"].lower()

    def test_borrow_out_of_stock_400(self, client, created_user):
        # create a book with zero stock
        r = client.post(
            "/api/v1/books/",
            json={"title": "Empty", "author": "A", "price": 5.0, "stock": 0},
        )
        book_id = r.json()["id"]
        payload = {
            "user_id": created_user["user"]["id"],
            "book_id": book_id,
            "return_deadline": "2099-01-01T00:00:00",
        }
        resp = client.post("/api/v1/orders/borrow", json=payload)
        assert resp.status_code == 400

    def test_borrow_missing_fields_422(self, client):
        resp = client.post("/api/v1/orders/borrow", json={"user_id": 1})
        assert resp.status_code == 422

    @pytest.mark.parametrize(
        "field,value",
        [
            ("user_id", 0),
            ("book_id", 0),
            ("user_id", -1),
            ("return_deadline", "2000-01-01T00:00:00"),
        ],
        ids=["user-id-zero", "book-id-zero", "user-id-negative", "past-deadline"],
    )
    def test_borrow_invalid_values_422(self, client, created_user, field, value):
        payload = {
            "user_id": created_user["user"]["id"],
            "book_id": 1,
            "return_deadline": "2099-01-01T00:00:00",
            field: value,
        }
        resp = client.post("/api/v1/orders/borrow", json=payload)
        assert resp.status_code == 422

    def test_borrow_extra_field_422(self, client, created_user, created_book):
        payload = {
            "user_id": created_user["user"]["id"],
            "book_id": created_book["book"]["id"],
            "return_deadline": "2099-01-01T00:00:00",
            "note": "rush",
        }
        resp = client.post("/api/v1/orders/borrow", json=payload)
        assert resp.status_code == 422


class TestReturnBook:
    def test_return_success_restores_stock(self, client, created_order, created_book):
        oid = created_order["order"]["id"]
        original_stock = created_book["book"]["stock"]

        resp = client.put(f"/api/v1/orders/{oid}/return")
        assert resp.status_code == 200
        body = resp.json()
        assert body["delivery_date"] is not None

        # stock must be restored to its original value
        book = next(
            b
            for b in client.get("/api/v1/books/").json()["items"]
            if b["id"] == created_book["book"]["id"]
        )
        assert book["stock"] == original_stock

    def test_double_return_rejected(self, client, created_order):
        oid = created_order["order"]["id"]
        assert client.put(f"/api/v1/orders/{oid}/return").status_code == 200
        resp = client.put(f"/api/v1/orders/{oid}/return")
        assert resp.status_code == 400
        assert "already been returned" in resp.json()["detail"]

    def test_return_missing_order_400(self, client):
        resp = client.put("/api/v1/orders/99999/return")
        assert resp.status_code == 400


class TestDelayedOrders:
    def test_no_delayed_orders_initially(self, client):
        resp = client.get("/api/v1/orders/delayed")
        assert resp.status_code == 200
        body = resp.json()
        assert body["items"] == []
        assert body["total"] == 0

    def test_overdue_order_appears_in_delayed_list(
        self, client, created_user, created_book, backdate_order
    ):
        # create an order (deadline must be in the future for validation),
        # then move the deadline into the past at the DB level.
        payload = {
            "user_id": created_user["user"]["id"],
            "book_id": created_book["book"]["id"],
            "return_deadline": "2099-01-01T00:00:00",
        }
        r = client.post("/api/v1/orders/borrow", json=payload)
        assert r.status_code == 200
        backdate_order(r.json()["id"])

        resp = client.get("/api/v1/orders/delayed")
        assert resp.status_code == 200
        ids = [o["id"] for o in resp.json()["items"]]
        assert r.json()["id"] in ids

    def test_returned_order_not_delayed(self, client, created_order, backdate_order):
        oid = created_order["order"]["id"]
        backdate_order(oid)
        assert client.put(f"/api/v1/orders/{oid}/return").status_code == 200

        body = client.get("/api/v1/orders/delayed").json()
        assert oid not in [o["id"] for o in body["items"]]


class TestFullWorkflow:
    """Full end-to-end scenario: register -> add book -> borrow -> return."""

    def test_full_lifecycle(self, client):
        # 1. Register a user
        u = client.post(
            "/api/v1/users/",
            json={
                "username": "workflow_user",
                "email": "wf@example.com",
                "password": "Passw0rd!xyz",
            },
        ).json()

        # 2. Add a book with 2 copies
        b = client.post(
            "/api/v1/books/",
            json={"title": "Lifecycle", "author": "QA", "price": 10.0, "stock": 2},
        ).json()

        # 3. Borrow twice
        deadline = "2099-06-01T00:00:00"
        o1 = client.post(
            "/api/v1/orders/borrow",
            json={"user_id": u["id"], "book_id": b["id"], "return_deadline": deadline},
        ).json()
        o2 = client.post(
            "/api/v1/orders/borrow",
            json={"user_id": u["id"], "book_id": b["id"], "return_deadline": deadline},
        ).json()

        # 4. The third borrow must fail because stock is exhausted
        r3 = client.post(
            "/api/v1/orders/borrow",
            json={"user_id": u["id"], "book_id": b["id"], "return_deadline": deadline},
        )
        assert r3.status_code == 400

        # 5. Returning one order -> stock becomes 1 again
        client.put(f"/api/v1/orders/{o1['id']}/return")
        book = next(bk for bk in client.get("/api/v1/books/").json()["items"] if bk["id"] == b["id"])
        assert book["stock"] == 1

        # 6. Borrowing again succeeds
        r4 = client.post(
            "/api/v1/orders/borrow",
            json={"user_id": u["id"], "book_id": b["id"], "return_deadline": deadline},
        )
        assert r4.status_code == 200
        assert r4.json()["id"] != o2["id"]


class TestStockGuard:
    """The borrow path must use an atomic conditional UPDATE (stock > 0)."""

    def test_cannot_borrow_more_copies_than_stock(self, client, created_user):
        r = client.post(
            "/api/v1/books/",
            json={"title": "Limited", "author": "A", "price": 5.0, "stock": 2},
        )
        book_id = r.json()["id"]
        payload = {
            "user_id": created_user["user"]["id"],
            "book_id": book_id,
            "return_deadline": "2099-01-01T00:00:00",
        }
        assert client.post("/api/v1/orders/borrow", json=payload).status_code == 200
        assert client.post("/api/v1/orders/borrow", json=payload).status_code == 200

        resp = client.post("/api/v1/orders/borrow", json=payload)
        assert resp.status_code == 400

        body = client.get("/api/v1/books/").json()["items"][0]
        assert body["stock"] == 0

    def test_failed_borrow_leaves_stock_untouched(self, client, created_user, created_book):
        payload = {
            "user_id": created_user["user"]["id"],
            "book_id": 99999,
            "return_deadline": "2099-01-01T00:00:00",
        }
        resp = client.post("/api/v1/orders/borrow", json=payload)
        assert resp.status_code == 400

        stock = client.get("/api/v1/books/").json()["items"][0]["stock"]
        assert stock == created_book["book"]["stock"]
