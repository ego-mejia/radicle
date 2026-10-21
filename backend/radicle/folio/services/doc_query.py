"""Querying docs with RQL (Folio 1.6): `space = ai-tools AND published >= -30d`.

Visibility is part of the same statement as the query, so a node you may not see never
matches, counts or sorts.
"""

import base64
import json
from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from radicle.folio.db.models import FolioNode, FolioSpace, FolioVersion
from radicle.folio.query.compiler import Context, Published, compile_query
from radicle.folio.services import access
from radicle.platform.db.models import User, utcnow
from radicle.platform.errors import ValidationFailed
from radicle.platform.query.parser import parse

DEFAULT_LIMIT = 20
MAX_LIMIT = 100


@dataclass(frozen=True)
class Doc:
    node: FolioNode
    space: str
    version: FolioVersion | None


@dataclass(frozen=True)
class Result:
    items: list[Doc]
    next_cursor: str | None


def _encode(offset: int) -> str:
    return base64.urlsafe_b64encode(json.dumps({"o": offset}).encode()).decode().rstrip("=")


def _decode(cursor: str | None) -> int:
    if not cursor:
        return 0
    try:
        offset = json.loads(base64.urlsafe_b64decode(cursor + "=" * (-len(cursor) % 4)))["o"]
    except (ValueError, KeyError, TypeError):
        offset = None
    if not isinstance(offset, int) or offset < 0:
        raise ValidationFailed(
            "Invalid cursor. Use next_cursor from the previous page with the same query.",
            errors=[{"field": "cursor", "message": "invalid"}],
        )
    return offset


async def query(
    db: AsyncSession,
    user: User,
    q: str,
    *,
    limit: int = DEFAULT_LIMIT,
    cursor: str | None = None,
    timezone: str = "UTC",
    now: datetime | None = None,
) -> Result:
    compiled = compile_query(
        parse(q), Context(user_id=user.id, now=now or utcnow(), tz=ZoneInfo(timezone))
    )
    offset = _decode(cursor)
    rows = await db.execute(
        select(FolioNode, FolioSpace.key, Published)
        .join(FolioSpace, FolioSpace.id == FolioNode.space_id)
        .outerjoin(Published, Published.id == FolioNode.published_version_id)
        .where(await access.node_filter(db, user), compiled.where)
        .order_by(*compiled.order_by)
        .offset(offset)
        .limit(limit + 1)
    )
    found = [Doc(node=n, space=key, version=v) for n, key, v in rows.all()]
    more = len(found) > limit
    return Result(items=found[:limit], next_cursor=_encode(offset + limit) if more else None)
