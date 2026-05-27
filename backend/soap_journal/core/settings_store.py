"""DB-backed runtime settings (the `settings` key/value table).

Distinct from `config.Settings`, which holds env-loaded boot config. Values
in this store are mutable at runtime via the admin API.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from soap_journal.db.models.setting import Setting

OPEN_REGISTRATION_KEY = "open_registration"


async def get_setting(db: AsyncSession, key: str) -> str | None:
    result = await db.execute(select(Setting).where(Setting.key == key))
    row = result.scalar_one_or_none()
    return row.value if row else None


async def set_setting(db: AsyncSession, key: str, value: str) -> None:
    result = await db.execute(select(Setting).where(Setting.key == key))
    row = result.scalar_one_or_none()
    if row is None:
        db.add(Setting(key=key, value=value))
    else:
        row.value = value
    await db.commit()


async def get_bool_setting(db: AsyncSession, key: str, default: bool) -> bool:
    value = await get_setting(db, key)
    if value is None:
        return default
    return value.strip().lower() == "true"


async def set_bool_setting(db: AsyncSession, key: str, value: bool) -> None:
    await set_setting(db, key, "true" if value else "false")


async def is_open_registration(db: AsyncSession) -> bool:
    return await get_bool_setting(db, OPEN_REGISTRATION_KEY, default=False)


async def set_open_registration(db: AsyncSession, value: bool) -> None:
    await set_bool_setting(db, OPEN_REGISTRATION_KEY, value)
