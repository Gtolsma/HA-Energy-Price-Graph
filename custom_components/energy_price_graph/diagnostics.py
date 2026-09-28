"""Diagnostics for Energy Price Graph."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from homeassistant.const import __version__ as HA_VERSION
from homeassistant.core import HomeAssistant

from . import (
    _VERSION,
    EnergyPriceGraphConfigEntry,
    frontend_reports,
)
from .const import DEFAULT_OPTIONS
from .forecast import CACHE_KEY
from .prefs import async_energy_setup


def _entity(hass: HomeAssistant, entity_id: str | None) -> dict[str, Any] | None:
    """State, unit and attribute names of a price sensor (no values)."""
    if not entity_id:
        return None
    state = hass.states.get(entity_id)
    if state is None:
        return {"entity_id": entity_id, "state": None}
    return {
        "entity_id": entity_id,
        "state": state.state,
        "unit_of_measurement": state.attributes.get("unit_of_measurement"),
        "state_class": state.attributes.get("state_class"),
        "attributes": sorted(state.attributes),
    }


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: EnergyPriceGraphConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    options = {**DEFAULT_OPTIONS, **entry.options}
    setup = await async_energy_setup(hass, options)
    forecast_cache = hass.data.get(CACHE_KEY) or {}
    return {
        "version": hass.data.get(_VERSION),
        "home_assistant": HA_VERSION,
        "options": options,
        "energy": asdict(setup) if setup else None,
        "price_sensors": {
            "import": _entity(hass, setup.import_price if setup else None),
            "export": _entity(hass, setup.export_price if setup else None),
            "gas": _entity(hass, setup.gas_price if setup else None),
        },
        "forecast_sources": {
            entity_id: {"source": r["source"], "points": len(r["points"])}
            for entity_id, (_, r) in forecast_cache.items()
        },
        "frontend_reports": frontend_reports(hass),
    }
