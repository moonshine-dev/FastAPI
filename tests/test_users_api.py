import pytest

pytestmark = pytest.mark.users


class TestRoot:
    def test_root(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        assert resp.json() == {"message": "Welcome to the Library Management System!"}


class TestRegisterUser:
    def test_register_user_success(self, client):
        payload = {
            "username": "sara_moradi",
            "email": "sara@example.com",
            "password": "Str0ng!pass",
        }
        resp = client.post("/users/", json=payload)
        assert resp.status_code == 200
        body = resp.json()
        assert body["id"] > 0
        assert body["username"] == payload["username"]
        assert body["email"] == payload["email"]
        assert body["is_active"] is True
        # the password must never appear in the response
        assert "password" not in body and "hashed_password" not in body

    @pytest.mark.parametrize(
        "payload",
        [
            # invalid email
            {"username": "u1", "email": "not-an-email", "password": "x"},
            # missing required fields
            {"email": "a@b.com", "password": "x"},
        ],
        ids=["invalid-email", "missing-username"],
    )
    def test_register_user_validation_error(self, client, payload):
        resp = client.post("/users/", json=payload)
        assert resp.status_code == 422

    def test_duplicate_username_rejected(self, client, created_user):
        payload = dict(created_user["payload"])
        payload["email"] = "other@example.com"
        resp = client.post("/users/", json=payload)
        assert resp.status_code == 400
        assert "already exists" in resp.json()["detail"]

    def test_stored_password_is_hashed(self, client, test_db, created_user):
        from models import User

        user_id = created_user["user"]["id"]
        row = test_db.query(User).filter(User.id == user_id).first()
        assert row.hashed_password != created_user["payload"]["password"]
        assert len(row.hashed_password) >= 50


class TestGetUserProfile:
    def test_get_existing_user(self, client, created_user):
        uid = created_user["user"]["id"]
        resp = client.get(f"/users/{uid}")
        assert resp.status_code == 200
        assert resp.json()["id"] == uid

    def test_get_missing_user_404(self, client):
        resp = client.get("/users/99999")
        assert resp.status_code == 404
        assert resp.json()["detail"] == "User not found"

    def test_get_user_invalid_id_type(self, client):
        resp = client.get("/users/abc")
        assert resp.status_code == 422
