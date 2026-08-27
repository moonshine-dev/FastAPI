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
        assert resp.json() == []

    def test_list_returns_created_books(self, client, created_book):
        resp = client.get("/books/")
        assert resp.status_code == 200
        books = resp.json()
        assert len(books) == 1
        assert books[0]["title"] == created_book["book"]["title"]

    def test_list_multiple_books(self, client):
        for i in range(3):
            r = client.post(
                "/books/",
                json={"title": f"B{i}", "author": f"A{i}", "price": i + 1.0, "stock": 2},
            )
            assert r.status_code == 200
        resp = client.get("/books/")
        assert {b["title"] for b in resp.json()} == {"B0", "B1", "B2"}
