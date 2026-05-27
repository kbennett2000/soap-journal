from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from soap_journal.core.cookies import COOKIE_NAME
from soap_journal.core.settings_store import set_open_registration
from soap_journal.db.models.user import User
from soap_journal.db.models.user_session import UserSession

# ---- helpers ---------------------------------------------------------------


async def _register(client: AsyncClient, username: str, password: str = "password123"):
    return await client.post(
        "/api/v1/auth/register",
        json={"username": username, "password": password},
    )


async def _login(client: AsyncClient, username: str, password: str = "password123"):
    client.cookies.clear()
    return await client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": password},
    )


async def _bootstrap_admin_and_second_user(
    client: AsyncClient, db: AsyncSession
) -> tuple[int, int]:
    """Register alice (admin via bootstrap) and bob (non-admin), then leave
    the client logged in as alice. Returns (alice_id, bob_id)."""
    assert (await _register(client, "alice")).status_code == 201
    await set_open_registration(db, True)
    assert (await _register(client, "bob")).status_code == 201
    bob_id = await _register_get_id(client, db, "bob")
    alice_id = await _register_get_id(client, db, "alice")
    # Switch back to alice's session for admin actions.
    assert (await _login(client, "alice")).status_code == 200
    return alice_id, bob_id


async def _register_get_id(client: AsyncClient, db: AsyncSession, username: str) -> int:
    result = await db.execute(select(User).where(User.username == username))
    return result.scalar_one().id


# ---- authorization ---------------------------------------------------------


async def test_admin_endpoint_unauthenticated_returns_401(
    client: AsyncClient,
) -> None:
    response = await client.get("/api/v1/admin/users")
    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "NOT_AUTHENTICATED"


async def test_admin_endpoint_non_admin_returns_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    assert (await _register(client, "alice")).status_code == 201
    await set_open_registration(db_session, True)
    assert (await _register(client, "bob")).status_code == 201
    # Client is now signed in as bob (non-admin).

    response = await client.get("/api/v1/admin/users")

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "ADMIN_REQUIRED"


# ---- user list -------------------------------------------------------------


async def test_list_users_returns_all_users_in_created_order(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    await _bootstrap_admin_and_second_user(client, db_session)

    response = await client.get("/api/v1/admin/users")

    assert response.status_code == 200
    body = response.json()
    usernames = [u["username"] for u in body["users"]]
    assert usernames == ["alice", "bob"]
    assert body["users"][0]["is_admin"] is True
    assert body["users"][1]["is_admin"] is False
    # password_hash should not leak.
    assert "password_hash" not in body["users"][0]


# ---- create user -----------------------------------------------------------


async def test_admin_create_user_happy_path(client: AsyncClient, db_session: AsyncSession) -> None:
    assert (await _register(client, "alice")).status_code == 201

    response = await client.post(
        "/api/v1/admin/users",
        json={"username": "bob", "password": "password123", "is_admin": False},
    )

    assert response.status_code == 201
    assert response.json()["user"]["username"] == "bob"
    assert response.json()["user"]["is_admin"] is False
    assert "password_hash" not in response.json()["user"]
    # Admin-create must not log the new user in: alice's cookie should
    # still authenticate.
    me = await client.get("/api/v1/auth/me")
    assert me.json()["user"]["username"] == "alice"


async def test_admin_create_user_can_create_admin(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    assert (await _register(client, "alice")).status_code == 201

    response = await client.post(
        "/api/v1/admin/users",
        json={"username": "carol", "password": "password123", "is_admin": True},
    )

    assert response.status_code == 201
    assert response.json()["user"]["is_admin"] is True


async def test_admin_create_user_duplicate_username_returns_409(
    client: AsyncClient,
) -> None:
    assert (await _register(client, "alice")).status_code == 201

    response = await client.post(
        "/api/v1/admin/users",
        json={"username": "ALICE", "password": "password123"},
    )

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "USERNAME_TAKEN"


async def test_admin_created_user_can_login(client: AsyncClient, db_session: AsyncSession) -> None:
    assert (await _register(client, "alice")).status_code == 201
    assert (
        await client.post(
            "/api/v1/admin/users",
            json={"username": "bob", "password": "bob-password"},
        )
    ).status_code == 201

    response = await _login(client, "bob", "bob-password")
    assert response.status_code == 200
    assert response.json()["user"]["username"] == "bob"


# ---- delete user -----------------------------------------------------------


async def test_admin_delete_user_removes_user_and_their_sessions(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    alice_id, bob_id = await _bootstrap_admin_and_second_user(client, db_session)
    # Capture a still-valid bob cookie before deleting him.
    assert (await _login(client, "bob")).status_code == 200
    bob_cookie = client.cookies.get(COOKIE_NAME)
    assert bob_cookie

    assert (await _login(client, "alice")).status_code == 200
    response = await client.delete(f"/api/v1/admin/users/{bob_id}")
    assert response.status_code == 204

    # Bob is gone from the list.
    listing = await client.get("/api/v1/admin/users")
    assert [u["username"] for u in listing.json()["users"]] == ["alice"]

    # Bob's old cookie no longer authenticates.
    client.cookies.clear()
    client.cookies.set(COOKIE_NAME, bob_cookie)
    me = await client.get("/api/v1/auth/me")
    assert me.status_code == 401

    # Sessions row is gone too.
    leftover = await db_session.execute(select(UserSession).where(UserSession.user_id == bob_id))
    assert leftover.scalar_one_or_none() is None


async def test_admin_cannot_delete_last_admin(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    assert (await _register(client, "alice")).status_code == 201
    alice_id = await _register_get_id(client, db_session, "alice")

    response = await client.delete(f"/api/v1/admin/users/{alice_id}")

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "LAST_ADMIN"


async def test_admin_can_delete_admin_when_another_exists(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    assert (await _register(client, "alice")).status_code == 201
    assert (
        await client.post(
            "/api/v1/admin/users",
            json={"username": "carol", "password": "password123", "is_admin": True},
        )
    ).status_code == 201
    carol_id = await _register_get_id(client, db_session, "carol")

    response = await client.delete(f"/api/v1/admin/users/{carol_id}")
    assert response.status_code == 204


async def test_admin_delete_unknown_user_returns_404(
    client: AsyncClient,
) -> None:
    assert (await _register(client, "alice")).status_code == 201
    response = await client.delete("/api/v1/admin/users/99999")
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "USER_NOT_FOUND"


# ---- reset password --------------------------------------------------------


async def test_admin_reset_password_lets_user_login_with_new_password(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    alice_id, bob_id = await _bootstrap_admin_and_second_user(client, db_session)

    response = await client.post(
        f"/api/v1/admin/users/{bob_id}/reset-password",
        json={"new_password": "brand-new-pw"},
    )
    assert response.status_code == 204

    # Old password no longer works.
    bad = await _login(client, "bob", "password123")
    assert bad.status_code == 401
    assert bad.json()["detail"]["code"] == "INVALID_CREDENTIALS"

    # New password does.
    good = await _login(client, "bob", "brand-new-pw")
    assert good.status_code == 200


async def test_admin_reset_password_invalidates_existing_sessions(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    alice_id, bob_id = await _bootstrap_admin_and_second_user(client, db_session)
    # Give bob a fresh session and snapshot its cookie.
    assert (await _login(client, "bob")).status_code == 200
    bob_cookie = client.cookies.get(COOKIE_NAME)

    assert (await _login(client, "alice")).status_code == 200
    assert (
        await client.post(
            f"/api/v1/admin/users/{bob_id}/reset-password",
            json={"new_password": "rotated-pw"},
        )
    ).status_code == 204

    # Replay bob's old cookie: it must be rejected.
    client.cookies.clear()
    client.cookies.set(COOKIE_NAME, bob_cookie)
    me = await client.get("/api/v1/auth/me")
    assert me.status_code == 401
    assert me.json()["detail"]["code"] == "NOT_AUTHENTICATED"


async def test_admin_reset_password_unknown_user_returns_404(
    client: AsyncClient,
) -> None:
    assert (await _register(client, "alice")).status_code == 201
    response = await client.post(
        "/api/v1/admin/users/99999/reset-password",
        json={"new_password": "whatever123"},
    )
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "USER_NOT_FOUND"


async def test_admin_reset_password_weak_rejected_by_schema(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    alice_id, bob_id = await _bootstrap_admin_and_second_user(client, db_session)
    response = await client.post(
        f"/api/v1/admin/users/{bob_id}/reset-password",
        json={"new_password": "short"},
    )
    assert response.status_code == 422


# ---- promote / demote ------------------------------------------------------


async def test_admin_promote_makes_non_admin_an_admin(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    alice_id, bob_id = await _bootstrap_admin_and_second_user(client, db_session)

    response = await client.post(f"/api/v1/admin/users/{bob_id}/promote")

    assert response.status_code == 200
    assert response.json()["user"]["is_admin"] is True


async def test_admin_promote_existing_admin_is_idempotent(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    assert (await _register(client, "alice")).status_code == 201
    alice_id = await _register_get_id(client, db_session, "alice")

    response = await client.post(f"/api/v1/admin/users/{alice_id}/promote")

    assert response.status_code == 200
    assert response.json()["user"]["is_admin"] is True


async def test_admin_promote_unknown_user_returns_404(
    client: AsyncClient,
) -> None:
    assert (await _register(client, "alice")).status_code == 201
    response = await client.post("/api/v1/admin/users/99999/promote")
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "USER_NOT_FOUND"


async def test_admin_demote_removes_admin_when_another_admin_exists(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    assert (await _register(client, "alice")).status_code == 201
    assert (
        await client.post(
            "/api/v1/admin/users",
            json={"username": "carol", "password": "password123", "is_admin": True},
        )
    ).status_code == 201
    carol_id = await _register_get_id(client, db_session, "carol")

    response = await client.post(f"/api/v1/admin/users/{carol_id}/demote")

    assert response.status_code == 200
    assert response.json()["user"]["is_admin"] is False


async def test_admin_demote_last_admin_returns_409(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    assert (await _register(client, "alice")).status_code == 201
    alice_id = await _register_get_id(client, db_session, "alice")

    response = await client.post(f"/api/v1/admin/users/{alice_id}/demote")

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "LAST_ADMIN"


async def test_admin_demote_non_admin_is_idempotent(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    alice_id, bob_id = await _bootstrap_admin_and_second_user(client, db_session)

    response = await client.post(f"/api/v1/admin/users/{bob_id}/demote")

    assert response.status_code == 200
    assert response.json()["user"]["is_admin"] is False


async def test_admin_demote_unknown_user_returns_404(
    client: AsyncClient,
) -> None:
    assert (await _register(client, "alice")).status_code == 201
    response = await client.post("/api/v1/admin/users/99999/demote")
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "USER_NOT_FOUND"


async def test_demoted_admin_keeps_session_but_loses_admin_authorization(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    # Two admins: alice (bootstrap) + carol (created as admin).
    assert (await _register(client, "alice")).status_code == 201
    assert (
        await client.post(
            "/api/v1/admin/users",
            json={"username": "carol", "password": "password123", "is_admin": True},
        )
    ).status_code == 201
    carol_id = await _register_get_id(client, db_session, "carol")

    # Carol logs in herself and confirms admin access.
    assert (await _login(client, "carol")).status_code == 200
    assert (await client.get("/api/v1/admin/users")).status_code == 200

    # Carol demotes herself.
    demote = await client.post(f"/api/v1/admin/users/{carol_id}/demote")
    assert demote.status_code == 200
    assert demote.json()["user"]["is_admin"] is False

    # /auth/me still works (session stayed valid) but admin endpoints reject.
    me = await client.get("/api/v1/auth/me")
    assert me.status_code == 200
    forbidden = await client.get("/api/v1/admin/users")
    assert forbidden.status_code == 403
    assert forbidden.json()["detail"]["code"] == "ADMIN_REQUIRED"


# ---- settings --------------------------------------------------------------


async def test_admin_get_settings_returns_seeded_defaults(
    client: AsyncClient,
) -> None:
    assert (await _register(client, "alice")).status_code == 201

    response = await client.get("/api/v1/admin/settings")

    assert response.status_code == 200
    assert response.json() == {"settings": {"open_registration": False}}


async def test_admin_put_settings_persists_open_registration(
    client: AsyncClient,
) -> None:
    assert (await _register(client, "alice")).status_code == 201

    put_resp = await client.put("/api/v1/admin/settings", json={"open_registration": True})
    assert put_resp.status_code == 200
    assert put_resp.json()["settings"]["open_registration"] is True

    get_resp = await client.get("/api/v1/admin/settings")
    assert get_resp.json()["settings"]["open_registration"] is True


async def test_admin_put_settings_opens_registration_end_to_end(
    client: AsyncClient,
) -> None:
    # Alice (admin) flips open_registration on; an unauthenticated stranger
    # can then register.
    assert (await _register(client, "alice")).status_code == 201
    assert (
        await client.put("/api/v1/admin/settings", json={"open_registration": True})
    ).status_code == 200

    # Drop alice's cookie and try as a "fresh" client.
    client.cookies.clear()
    response = await _register(client, "stranger", "password123")
    assert response.status_code == 201


async def test_admin_put_settings_rejects_unknown_field(
    client: AsyncClient,
) -> None:
    assert (await _register(client, "alice")).status_code == 201

    response = await client.put(
        "/api/v1/admin/settings",
        json={"open_registration": False, "future_thing": True},
    )

    assert response.status_code == 422
