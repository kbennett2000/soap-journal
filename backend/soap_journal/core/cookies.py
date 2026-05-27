from fastapi import Response

COOKIE_NAME = "soap_session"
COOKIE_MAX_AGE = 60 * 60 * 24 * 30  # 30 days
COOKIE_PATH = "/"
COOKIE_HTTPONLY = True
COOKIE_SECURE = False  # LAN deployments are typically HTTP
COOKIE_SAMESITE = "lax"


def set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        max_age=COOKIE_MAX_AGE,
        path=COOKIE_PATH,
        httponly=COOKIE_HTTPONLY,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(key=COOKIE_NAME, path=COOKIE_PATH)
