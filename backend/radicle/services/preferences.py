"""Per-person UI preferences: theme, language, shortcuts and density."""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from radicle.core.errors import ValidationFailed
from radicle.db.models import User, UserPreferences

DEFAULTS: dict[str, Any] = {
    "theme": "system",
    "language": None,
    "shortcuts": True,
    "density": "comfortable",
}
CHOICES: dict[str, tuple[Any, ...]] = {
    "theme": ("system", "light", "dark"),
    "language": (None, "en", "es"),
    "shortcuts": (True, False),
    "density": ("comfortable", "compact"),
}


async def get_preferences(db: AsyncSession, user: User) -> dict[str, Any]:
    row = await db.get(UserPreferences, user.id)
    return {**DEFAULTS, **(row.prefs if row else {})}


async def update_preferences(
    db: AsyncSession, user: User, changes: dict[str, Any]
) -> dict[str, Any]:
    for key, value in changes.items():
        if key not in CHOICES:
            raise ValidationFailed(
                f"Unknown preference '{key}'. Preferences: {', '.join(CHOICES)}.",
                errors=[{"field": key, "message": "unknown"}],
            )
        if value not in CHOICES[key]:
            options = ", ".join(str(v).lower() if v is not None else "null" for v in CHOICES[key])
            raise ValidationFailed(
                f"{key} must be one of: {options}.", errors=[{"field": key, "message": "invalid"}]
            )
    row = await db.get(UserPreferences, user.id)
    if row is None:
        row = UserPreferences(user_id=user.id, prefs={})
        db.add(row)
    row.prefs = {**row.prefs, **changes}
    await db.flush()
    return {**DEFAULTS, **row.prefs}
