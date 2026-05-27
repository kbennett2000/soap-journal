import asyncio
from datetime import UTC

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from soap_journal.core.cookies import COOKIE_NAME
from soap_journal.core.settings_store import OPEN_REGISTRATION_KEY
from soap_journal.db.models.setting import Setting
from soap_journal.db.models.user import User
from soap_journal.db.models.user_session import UserSession


async def _set_open_registration(db: AsyncSession, value: bool) -> None:
    result = await db.execute(select(Setting).where(Setting.key == OPEN_REGISTRATION_KEY))
    row = result.scalar_one_or_none()
    new_value = "true" if value else "false"
    if row is None:
        db.add(Setting(key=OPEN_REGISTRATION_KEY, value=new_value))
    else:
        row.value = new_value
    await db.commit()


async def _register(client: AsyncClient, username: str, password: str = "password123"):
    return await client.post(
        "/api/v1/auth/register",
        json={"username": username, "password": password},
    )


# ----- registration ---------------------------------------------------------


async def test_first_registration_creates_admin_even_when_registration_closed(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    await _set_open_registration(db_session, False)

    response = await _register(client, "alice")

    assert response.status_code == 201
    body = response.json()
    assert body["user"]["username"] == "alice"
    assert body["user"]["is_admin"] is True
    assert COOKIE_NAME in response.cookies


async def test_second_registration_blocked_when_registration_closed(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    await _set_open_registration(db_session, False)
    assert (await _register(client, "alice")).status_code == 201

    response = await _register(client, "bob")

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "REGISTRATION_CLOSED"


async def test_second_registration_when_open_creates_non_admin(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    assert (await _register(client, "alice")).status_code == 201
    await _set_open_registration(db_session, True)

    response = await _register(client, "bob")

    assert response.status_code == 201
    assert response.json()["user"]["is_admin"] is False


async def test_duplicate_username_returns_409(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    assert (await _register(client, "alice")).status_code == 201
    # Open registration so the duplicate-username path is reachable; with
    # registration closed, REGISTRATION_CLOSED would fire first.
    await _set_open_registration(db_session, True)

    response = await _register(client, "alice")

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "USERNAME_TAKEN"


async def test_duplicate_username_is_case_insensitive(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    assert (await _register(client, "alice")).status_code == 201
    await _set_open_registration(db_session, True)

    response = await _register(client, "ALICE")

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "USERNAME_TAKEN"


async def test_username_validation_rejects_invalid_characters(
    client: AsyncClient,
) -> None:
    response = await client.post(
        "/api/v1/auth/register",
        json={"username": "alice!", "password": "password123"},
    )
    assert response.status_code == 422


async def test_password_too_short_rejected(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/auth/register",
        json={"username": "alice", "password": "short"},
    )
    assert response.status_code == 422


# ----- login ----------------------------------------------------------------


async def test_login_with_correct_credentials_sets_cookie(
    client: AsyncClient,
) -> None:
    assert (await _register(client, "alice", "password123")).status_code == 201
    # Drop the cookie that register set so login is exercised cleanly.
    client.cookies.clear()

    response = await client.post(
        "/api/v1/auth/login",
        json={"username": "alice", "password": "password123"},
    )

    assert response.status_code == 200
    assert response.json()["user"]["username"] == "alice"
    assert COOKIE_NAME in response.cookies


async def test_login_username_lookup_is_case_insensitive(
    client: AsyncClient,
) -> None:
    assert (await _register(client, "alice", "password123")).status_code == 201
    client.cookies.clear()

    response = await client.post(
        "/api/v1/auth/login",
        json={"username": "ALICE", "password": "password123"},
    )
    assert response.status_code == 200


async def test_login_with_wrong_password_returns_invalid_credentials(
    client: AsyncClient,
) -> None:
    assert (await _register(client, "alice", "password123")).status_code == 201
    client.cookies.clear()

    response = await client.post(
        "/api/v1/auth/login",
        json={"username": "alice", "password": "wrong-password"},
    )

    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "INVALID_CREDENTIALS"
    assert COOKIE_NAME not in response.cookies


async def test_login_with_unknown_user_returns_same_shape_as_wrong_password(
    client: AsyncClient,
) -> None:
    assert (await _register(client, "alice", "password123")).status_code == 201
    client.cookies.clear()

    wrong_pw = await client.post(
        "/api/v1/auth/login",
        json={"username": "alice", "password": "wrong-password"},
    )
    unknown_user = await client.post(
        "/api/v1/auth/login",
        json={"username": "nobody", "password": "whatever123"},
    )

    assert wrong_pw.status_code == 401
    assert unknown_user.status_code == 401
    assert wrong_pw.json() == unknown_user.json()


# ----- /auth/me -------------------------------------------------------------


async def test_me_without_cookie_returns_401(client: AsyncClient) -> None:
    response = await client.get("/api/v1/auth/me")

    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "NOT_AUTHENTICATED"


async def test_me_with_valid_cookie_returns_user_and_extends_session(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    assert (await _register(client, "alice")).status_code == 201

    user_row = (await db_session.execute(select(User).where(User.username == "alice"))).scalar_one()
    session_row = (
        await db_session.execute(select(UserSession).where(UserSession.user_id == user_row.id))
    ).scalar_one()
    original_expires = session_row.expires_at
    if original_expires.tzinfo is None:
        original_expires = original_expires.replace(tzinfo=UTC)

    # Wait long enough for wall-clock to advance past microsecond resolution
    # so the extended expires_at is strictly greater than the original.
    await asyncio.sleep(0.05)

    response = await client.get("/api/v1/auth/me")

    assert response.status_code == 200
    assert response.json()["user"]["username"] == "alice"

    await db_session.refresh(session_row)
    new_expires = session_row.expires_at
    if new_expires.tzinfo is None:
        new_expires = new_expires.replace(tzinfo=UTC)
    assert new_expires > original_expires


async def test_me_with_bogus_cookie_returns_401(client: AsyncClient) -> None:
    client.cookies.set(COOKIE_NAME, "not-a-real-token")
    response = await client.get("/api/v1/auth/me")

    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "NOT_AUTHENTICATED"


# ----- logout ---------------------------------------------------------------


async def test_logout_invalidates_session_and_clears_cookie(
    client: AsyncClient,
) -> None:
    assert (await _register(client, "alice")).status_code == 201
    # Confirm we're authenticated to start.
    assert (await client.get("/api/v1/auth/me")).status_code == 200

    # Capture the original token so we can simulate "browser kept the cookie"
    # after server-side invalidation.
    original_token = client.cookies.get(COOKIE_NAME)
    assert original_token

    logout_response = await client.post("/api/v1/auth/logout")
    assert logout_response.status_code == 204

    # Reset the cookie to the now-invalidated token and confirm /me rejects it.
    client.cookies.set(COOKIE_NAME, original_token)
    me_response = await client.get("/api/v1/auth/me")
    assert me_response.status_code == 401
    assert me_response.json()["detail"]["code"] == "NOT_AUTHENTICATED"


async def test_logout_is_idempotent_without_cookie(client: AsyncClient) -> None:
    response = await client.post("/api/v1/auth/logout")
    assert response.status_code == 204


async def test_logout_with_invalid_token_still_returns_204(
    client: AsyncClient,
) -> None:
    client.cookies.set(COOKIE_NAME, "garbage-token")
    response = await client.post("/api/v1/auth/logout")
    assert response.status_code == 204
