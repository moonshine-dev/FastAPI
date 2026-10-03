import pytest

pytestmark = pytest.mark.include


def borrow(client, user_id, book_id, deadline="2099-01-01T00:00:00"):
    resp = client.post(
        "/api/v1/orders/borrow",
        json={"user_id": user_id, "book_id": book_id, "return_deadline": deadline},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


class TestIncludeOnSingleUser:
    def test_without_include_has_no_orders_key(self, client, created_user):
        uid = created_user["user"]["id"]
        body = client.get(f"/api/v1/users/{uid}").json()
        assert body["id"] == uid
        assert "orders" not in body

    def test_include_orders_returns_nested_orders(self, client, created_user, created_book):
        uid = created_user["user"]["id"]
        bid = created_book["book"]["id"]
        o1 = borrow(client, uid, bid)
        o2 = borrow(client, uid, bid)

        body = client.get(f"/api/v1/users/{uid}", params={"include": "orders"}).json()
        assert body["id"] == uid
        assert "orders" in body
        assert {o["id"] for o in body["orders"]} == {o1["id"], o2["id"]}
        # nested orders keep the full OrderResponse shape
        order = body["orders"][0]
        assert {"id", "user_id", "book_id", "order_date", "return_deadline", "delivery_date"} <= set(order)

    def test_include_orders_empty_list(self, client, created_user):
        uid = created_user["user"]["id"]
        body = client.get(f"/api/v1/users/{uid}", params={"include": "orders"}).json()
        assert body["orders"] == []

    @pytest.mark.parametrize(
        "include",
        ["books", "orders,books", ""],
        ids=["unknown-resource", "mixed", "empty"],
    )
    def test_invalid_include_value_422(self, client, created_user, include):
        uid = created_user["user"]["id"]
        resp = client.get(f"/api/v1/users/{uid}", params={"include": include})
        assert resp.status_code == 422

    def test_unknown_user_with_include_404(self, client):
        resp = client.get("/api/v1/users/99999", params={"include": "orders"})
        assert resp.status_code == 404


class TestIncludeOnUserList:
    def test_list_without_include(self, client, created_user, created_book):
        uid = created_user["user"]["id"]
        borrow(client, uid, created_book["book"]["id"])

        body = client.get("/api/v1/users/").json()
        assert body["total"] == 1
        assert "orders" not in body["items"][0]

    def test_list_with_include_orders(self, client, created_user, created_book):
        uid = created_user["user"]["id"]
        bid = created_book["book"]["id"]
        o1 = borrow(client, uid, bid)
        borrow(client, uid, bid)

        body = client.get("/api/v1/users/", params={"include": "orders"}).json()
        assert body["total"] == 1
        item = body["items"][0]
        assert item["id"] == uid
        assert len(item["orders"]) == 2
        assert o1["id"] in [o["id"] for o in item["orders"]]

    def test_list_with_include_is_paginated(self, client, backdate_order):
        for i in range(3):
            resp = client.post(
                "/api/v1/users/",
                json={
                    "username": f"paged_user_{i}",
                    "email": f"paged{i}@example.com",
                    "password": "Str0ng!pass",
                },
            )
            assert resp.status_code == 200

        body = client.get(
            "/api/v1/users/", params={"page": 2, "size": 2, "include": "orders"}
        ).json()
        assert body["total"] == 3
        assert body["pages"] == 2
        assert len(body["items"]) == 1
        assert body["items"][0]["orders"] == []

    def test_user_without_orders_still_returned(self, client, created_user, created_book):
        # another user borrows, the first one must still have orders: []
        other = client.post(
            "/api/v1/users/",
            json={
                "username": "other_borrower",
                "email": "other@example.com",
                "password": "Str0ng!pass",
            },
        ).json()
        borrow(client, other["id"], created_book["book"]["id"])

        body = client.get("/api/v1/users/", params={"include": "orders"}).json()
        by_id = {u["id"]: u for u in body["items"]}
        assert by_id[created_user["user"]["id"]]["orders"] == []
        assert len(by_id[other["id"]]["orders"]) == 1
