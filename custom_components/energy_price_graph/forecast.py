"""Upcoming prices from integrations that provide them through an action.

Some price integrations do not put the upcoming prices in the attributes of
their sensors but offer an action (service) that returns them, for example
Nord Pool, Tibber, EnergyZero and easyEnergy in Home Assistant core. The
frontend asks for them over the websocket API when a forecast sensor has no
usable attributes. Values are returned in the unit of the integration; the
frontend scales them to the unit of the price sensor.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta
import logging
import time
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

CACHE_KEY = f"{DOMAIN}_forecast_cache"
CACHE_SECONDS = 15 * 60
TIMEOUT_SECONDS = 20

Points = list[tuple[datetime, float]]


def _point(start: Any, value: Any) -> tuple[datetime, float] | None:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return None
    if isinstance(start, datetime):
        ts = start
    elif isinstance(start, str):
        ts = dt_util.parse_datetime(start)
    else:
        ts = None
    if ts is None:
        return None
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=dt_util.get_default_time_zone())
    return ts, float(value)


def points_from(items: Any, time_key: str, value_key: str) -> Points:
    """Convert a list of {time_key, value_key} dicts to points."""
    out: Points = []
    for item in items or []:
        if isinstance(item, dict) and (
            p := _point(item.get(time_key), item.get(value_key))
        ):
            out.append(p)
    return out


async def _call(
    hass: HomeAssistant, domain: str, service: str, data: dict[str, Any]
) -> dict[str, Any]:
    async with asyncio.timeout(TIMEOUT_SECONDS):
        response = await hass.services.async_call(
            domain, service, data, blocking=True, return_response=True
        )
    return response if isinstance(response, dict) else {}


def _day_bounds() -> tuple[datetime, datetime]:
    """Start of today and the end of tomorrow, local time."""
    start = dt_util.start_of_local_day()
    return start, start + timedelta(days=2)


async def _nordpool(hass: HomeAssistant, entry: er.RegistryEntry) -> Points:
    config_entry = hass.config_entries.async_get_entry(entry.config_entry_id or "")
    if config_entry is None:
        return []
    areas = [str(a).upper() for a in config_entry.data.get("areas") or []]
    tokens = [t.upper() for t in (entry.unique_id or "").split("-")]
    area = next((a for a in areas if a in tokens), areas[0] if areas else None)
    if area is None:
        return []
    start, _ = _day_bounds()
    points: Points = []
    for day in (start.date(), start.date() + timedelta(days=1)):
        try:
            response = await _call(
                hass,
                "nordpool",
                "get_prices_for_date",
                {
                    "config_entry": config_entry.entry_id,
                    "date": day.isoformat(),
                    "areas": [area],
                },
            )
        except (HomeAssistantError, TimeoutError):
            # Tomorrow's prices are published around 13:00 CET.
            continue
        points += points_from(response.get(area), "start", "price")
    return points


async def _tibber(hass: HomeAssistant, entry: er.RegistryEntry) -> Points:
    start, end = _day_bounds()
    response = await _call(
        hass,
        "tibber",
        "get_prices",
        {
            "start": start.strftime("%Y-%m-%d %H:%M:%S"),
            "end": end.strftime("%Y-%m-%d %H:%M:%S"),
        },
    )
    homes = response.get("prices") or {}
    for prices in homes.values():
        if points := points_from(prices, "start_time", "price"):
            return points
    return []


def _dated(start: datetime, end: datetime) -> list[dict[str, str]]:
    """Today and tomorrow; if that fails, only today (the default)."""
    return [
        {
            "start": start.strftime("%Y-%m-%d %H:%M:%S"),
            "end": (end - timedelta(seconds=1)).strftime("%Y-%m-%d %H:%M:%S"),
        },
        {},
    ]


async def _timestamp_prices(
    hass: HomeAssistant, entry: er.RegistryEntry, domain: str, service: str
) -> Points:
    start, end = _day_bounds()
    for extra in _dated(start, end):
        try:
            response = await _call(
                hass,
                domain,
                service,
                {"config_entry": entry.config_entry_id, "incl_vat": True, **extra},
            )
        except (HomeAssistantError, TimeoutError):
            continue
        if points := points_from(response.get("prices"), "timestamp", "price"):
            return points
    return []


async def _energyzero(hass: HomeAssistant, entry: er.RegistryEntry) -> Points:
    service = (
        "get_gas_prices" if "gas" in (entry.unique_id or "") else "get_energy_prices"
    )
    return await _timestamp_prices(hass, entry, "energyzero", service)


async def _easyenergy(hass: HomeAssistant, entry: er.RegistryEntry) -> Points:
    unique_id = entry.unique_id or ""
    if "gas" in unique_id:
        service = "get_gas_prices"
    elif "return" in unique_id:
        service = "get_energy_return_prices"
    else:
        service = "get_energy_usage_prices"
    return await _timestamp_prices(hass, entry, "easyenergy", service)


PROVIDERS: dict[str, Callable[[HomeAssistant, er.RegistryEntry], Awaitable[Points]]] = {
    "nordpool": _nordpool,
    "tibber": _tibber,
    "energyzero": _energyzero,
    "easyenergy": _easyenergy,
}


async def async_get_forecast(hass: HomeAssistant, entity_id: str) -> dict[str, Any]:
    """Upcoming prices for a price sensor, from its integration's action."""
    cache: dict[str, tuple[float, dict[str, Any]]] = hass.data.setdefault(CACHE_KEY, {})
    if (hit := cache.get(entity_id)) and time.monotonic() - hit[0] < CACHE_SECONDS:
        return hit[1]

    result: dict[str, Any] = {"source": None, "points": []}
    entry = er.async_get(hass).async_get(entity_id)
    provider = PROVIDERS.get(entry.platform) if entry else None
    if entry and provider and hass.services.async_services_for_domain(entry.platform):
        try:
            points = await provider(hass, entry)
        except Exception as err:  # noqa: BLE001 - best effort, never break the graph
            _LOGGER.debug("Could not get upcoming prices for %s: %s", entity_id, err)
            points = []
        unique = {ts: value for ts, value in points}
        result = {
            "source": entry.platform,
            "points": [[ts.isoformat(), unique[ts]] for ts in sorted(unique)],
        }
    cache[entity_id] = (time.monotonic(), result)
    return result
