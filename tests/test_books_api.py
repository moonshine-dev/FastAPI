import pytest

pytestmark = pytest.mark.books


class TestCreateBook:
    def test_create_book_success(self, client):
        payload = {
            "title": "Clean Code",
            "author": "Robert C. Martin",
            "price": 30.0,
            "stock": 5,
            "description": None,
        }
        resp = client.post("/books/", json=payload)
        assert resp.status_code == 200
        body = resp.json()
        assert body["title"] == payload["title"]
        assert body["author"] == payload["author"]
        assert body["price"] == payload["price"]
        assert body["stock"] == payload["stock"]

    @pytest.mark.parametrize(
        "field",
        ["title", "author", "price", "stock"],
        ids=["no-title", "no-author", "no-price", "no-stock"],
    )
    def test_create_book_missing_required_field(self, client, field):
        payload = {
            "title": "T",
            "author": "A",
            "price": 1.0,
            "stock": 1,
        }
        payload.pop(field)
        resp = client.post("/books/", json=payload)
        assert resp.status_code == 422

    def test_description_is_optional(self, client):
        payload = {"title": "No Desc", "author": "Anon", "price": 9.9, "stock": 1}
        resp = client.post("/books/", json=payload)
        assert resp.status_code == 200
        assert resp.json()["description"] is None


class TestListBooks:
    def test_empty_list_initially(self, client):
        resp = client.get("/books/")
        assert resp.status_code == 200
        body = resp.json()
        assert body["items"] == []
        assert body["total"] == 0
        assert body["page"] == 1
        assert body["size"] == 10
        assert body["pages"] == 0

    def test_list_returns_created_books(self, client, created_book):
        resp = client.get("/books/")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 1
        assert len(body["items"]) == 1
        assert body["items"][0]["title"] == created_book["book"]["title"]

    def test_list_multiple_books(self, client):
        for i in range(3):
            r = client.post(
                "/books/",
                json={"title": f"B{i}", "author": f"A{i}", "price": i + 1.0, "stock": 2},
            )
            assert r.status_code == 200
        resp = client.get("/books/")
        assert {b["title"] for b in resp.json()["items"]} == {"B0", "B1", "B2"}


def seed_books(client, count):
    for i in range(count):
        r = client.post(
            "/books/",
            json={"title": f"B{i:02d}", "author": f"A{i:02d}", "price": 1.0, "stock": 1},
        )
        assert r.status_code == 200


class TestPagination:
    def test_default_page_and_size(self, client):
        seed_books(client, 15)
        resp = client.get("/books/")
        assert resp.status_code == 200
        body = resp.json()
        assert body["page"] == 1
        assert body["size"] == 10
        assert len(body["items"]) == 10
        assert body["total"] == 15
        assert body["pages"] == 2

    def test_second_page_returns_remaining_items(self, client):
        seed_books(client, 15)
        body = client.get("/books/", params={"page": 2, "size": 10}).json()
        assert len(body["items"]) == 5
        assert body["items"][0]["title"] == "B10"
        assert body["items"][-1]["title"] == "B14"

    def test_out_of_range_page_returns_empty_items(self, client):
        seed_books(client, 5)
        body = client.get("/books/", params={"page": 3, "size": 10}).json()
        assert body["items"] == []
        assert body["total"] == 5
        assert body["pages"] == 1

    @pytest.mark.parametrize(
        "params",
        [{"page": 0}, {"page": -1}, {"size": 0}, {"size": 101}],
        ids=["page-zero", "page-negative", "size-zero", "size-too-large"],
    )
    def test_invalid_pagination_params_422(self, client, params):
        resp = client.get("/books/", params=params)
        assert resp.status_code == 422

    def test_delayed_endpoint_is_paginated(self, client, created_user, created_book):
        for _ in range(3):
            r = client.post(
                "/orders/borrow",
                json={
                    "user_id": created_user["user"]["id"],
                    "book_id": created_book["book"]["id"],
                    "return_deadline": "2000-01-01T00:00:00",
                },
            )
            assert r.status_code == 200
        body = client.get("/orders/delayed", params={"page": 1, "size": 2}).json()
        assert body["total"] == 3
        assert body["pages"] == 2
        assert len(body["items"]) == 2


def seed_book(client, title):
    r = client.post(
        "/books/",
        json={"title": title, "author": "A", "price": 1.0, "stock": 1},
    )
    assert r.status_code == 200
    return r.json()


class TestSearchBooks:
    def test_exact_title_match(self, client):
        book = seed_book(client, "Clean Code")
        body = client.get("/books/search", params={"title": "Clean Code"}).json()
        assert body["total"] == 1
        assert body["items"][0]["id"] == book["id"]

    def test_partial_title_does_not_match(self, client):
        seed_book(client, "Clean Code")
        body = client.get("/books/search", params={"title": "Clean"}).json()
        assert body["items"] == []
        assert body["total"] == 0

    def test_search_is_case_sensitive(self, client):
        seed_book(client, "Clean Code")
        body = client.get("/books/search", params={"title": "clean code"}).json()
        assert body["items"] == []
        assert body["total"] == 0

    def test_search_no_match_returns_empty_page(self, client):
        seed_book(client, "Clean Code")
        body = client.get("/books/search", params={"title": "Unknown"}).json()
        assert body["items"] == []
        assert body["total"] == 0
        assert body["page"] == 1
        assert body["pages"] == 0

    def test_search_missing_title_param_422(self, client):
        resp = client.get("/books/search")
        assert resp.status_code == 422

    def test_search_is_paginated(self, client):
        for i in range(3):
            seed_book(client, "Duplicate Title")
        body = client.get(
            "/books/search", params={"title": "Duplicate Title", "page": 1, "size": 2}
        ).json()
        assert body["total"] == 3
        assert body["pages"] == 2
        assert len(body["items"]) == 2
