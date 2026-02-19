"""Background server sync: polls external bare-metal API and upserts into DB.

sync_servers() is designed to be called both by APScheduler and by the
manual trigger endpoint. It never raises on individual server failures.
"""

import logging

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.repositories.server_repo import ServerRepository

logger = logging.getLogger(__name__)

_TIER_HIGH = "high_performance"
_TIER_REGULAR = "regular"


def _classify_tier(cpu: int | None) -> str:
    if cpu is not None and cpu >= settings.PERFORMANCE_TIER_CPU_THRESHOLD:
        return _TIER_HIGH
    return _TIER_REGULAR


async def sync_servers(
    session: AsyncSession,
    http_client: httpx.AsyncClient,
) -> dict[str, int]:
    """Fetch the external server list, upsert into DB, mark missing as offline.

    Returns {"synced": int, "updated": int, "marked_offline": int}.
    """
    try:
        response = await http_client.get(
            settings.EXTERNAL_SERVER_API_URL,
            timeout=settings.EXTERNAL_API_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        raw_servers: list[dict] = response.json()
    except Exception as exc:
        logger.warning("Failed to fetch external server list: %s", exc)
        return {"synced": 0, "updated": 0, "marked_offline": 0}

    processed: list[dict] = []
    seen_names: list[str] = []

    for raw in raw_servers:
        try:
            cpu = raw.get("cpu")
            entry = {
                "name": raw["name"],
                "vendor": raw.get("vendor"),
                "site": raw.get("site"),
                "deployment_cluster": raw.get("deployment_cluster"),
                "cpu": cpu,
                "ram_gb": raw.get("ram_gb"),
                "serial_number": raw.get("serial_number"),
                "product": raw.get("product"),
                "performance_tier": _classify_tier(cpu),
            }
            processed.append(entry)
            seen_names.append(raw["name"])
        except (KeyError, TypeError) as exc:
            logger.warning("Skipping malformed server entry: %s — %s", raw, exc)

    repo = ServerRepository(session)
    counts = await repo.upsert_from_external(processed)
    marked_offline = await repo.mark_offline(seen_names)

    return {
        "synced": counts["inserted"],
        "updated": counts["updated"],
        "marked_offline": marked_offline,
    }
