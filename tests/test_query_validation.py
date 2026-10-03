import pytest

pytestmark = pytest.mark.query

LIST_ENDPOINTS = [
    "/api/v1/books/",
    "/api/v1/users/",
    "/api/v1/orders/delayed",
]


@pytest.mark.parametrize("endpoint", LIST_ENDPOINTS)
class TestPaginationQueryValidation:
    @pytest.mark.parametrize(
        "params",
        [
            {"page": 0},
            {"page": -1},
            {"size": 0},
            {"size": -5},
            {"size": 101},
            {"page": "abc"},
            {"size": "abc"},
            {"page": 1.5},
        ],
        ids=[
            "page-zero",
            "page-negative",
            "size-zero",
            "size-negative",
            "size-too-large",
            "page-not-int",
            "size-not-int",
            "page-float",
        ],
    )
    def test_invalid_pagination_422(self, client, endpoint, params):
        resp = client.get(endpoint, params=params)
        assert resp.status_code == 422

    @pytest.mark.parametrize(
        "params",
        [
            {"page": 1, "size": 1},
            {"page": 100, "size": 100},
            {"size": 10},
        ],
        ids=["minimum", "maximum", "default-page"],
    )
    def test_valid_pagination_accepted(self, client, endpoint, params):
        resp = client.get(endpoint, params=params)
        assert resp.status_code == 200

    def test_defaults_are_applied(self, client, endpoint):
        body = client.get(endpoint).json()
        assert body["page"] == 1
        assert body["size"] == 10


class TestSearchQueryValidation:
    @pytest.mark.parametrize(
        "params",
        [
            {"title": ""},
            {"title": "x" * 101},
            {"title": "ok", "page": 0},
            {"title": "ok", "size": 1000},
            {"title": "ok", "page": "abc"},
        ],
        ids=[
            "empty-title",
            "too-long-title",
            "bad-page",
            "bad-size",
            "page-not-int",
        ],
    )
    def test_search_invalid_params_422(self, client, params):
        resp = client.get("/api/v1/books/search", params=params)
        assert resp.status_code == 422

    def test_search_missing_title_422(self, client):
        assert client.get("/api/v1/books/search").status_code == 422
