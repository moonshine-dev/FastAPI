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
        resp = client.post("/api/v1/users/", json=payload)
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
            {"username": "u1xx", "email": "not-an-email", "password": "Str0ng!pass"},
            # missing required fields
            {"email": "a@b.com", "password": "Str0ng!pass"},
            # weak password (too short)
            {"username": "u1xx", "email": "a@b.com", "password": "Ab1!"},
            # password without a digit
            {"username": "u1xx", "email": "a@b.com", "password": "OnlyLetters"},
            # password without a letter
            {"username": "u1xx", "email": "a@b.com", "password": "12345678"},
            # username with illegal characters
            {"username": "bad user!", "email": "a@b.com", "password": "Str0ng!pass"},
            # reserved username
            {"username": "admin", "email": "a@b.com", "password": "Str0ng!pass"},
            # unknown extra field
            {
                "username": "u1xx",
                "email": "a@b.com",
                "password": "Str0ng!pass",
                "is_admin": True,
            },
        ],
        ids=[
            "invalid-email",
            "missing-username",
            "short-password",
            "password-no-digit",
            "password-no-letter",
            "bad-username",
            "reserved-username",
            "extra-field",
        ],
    )
    def test_register_user_validation_error(self, client, payload):
        resp = client.post("/api/v1/users/", json=payload)
        assert resp.status_code == 422

    def test_duplicate_username_rejected(self, client, created_user):
        payload = dict(created_user["payload"])
        payload["email"] = "other@example.com"
        resp = client.post("/api/v1/users/", json=payload)
        assert resp.status_code == 400
        assert "already exists" in resp.json()["detail"]

    def test_stored_password_is_hashed(self, client, test_db, created_user):
        from app.users.models import User

        user_id = created_user["user"]["id"]
        row = test_db.query(User).filter(User.id == user_id).first()
        assert row.hashed_password != created_user["payload"]["password"]
        assert len(row.hashed_password) >= 50


class TestGetUserProfile:
    def test_get_existing_user(self, client, created_user):
        uid = created_user["user"]["id"]
        resp = client.get(f"/api/v1/users/{uid}")
        assert resp.status_code == 200
        assert resp.json()["id"] == uid

    def test_get_missing_user_404(self, client):
        resp = client.get("/api/v1/users/99999")
        assert resp.status_code == 404
        assert resp.json()["detail"] == "User not found"

    def test_get_user_invalid_id_type(self, client):
        resp = client.get("/api/v1/users/abc")
        assert resp.status_code == 422
