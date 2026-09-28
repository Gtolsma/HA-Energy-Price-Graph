"""Read the price sensors and grid statistics from the energy preferences.

Supports the current schema (prices and statistics directly on the grid
source) and the older one (flow_from / flow_to lists), like the frontend.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from homeassistant.components.energy.data import async_get_manager
from homeassistant.core import HomeAssistant

from .const import CONF_EXPORT_ENTITY, CONF_GAS_ENTITY, CONF_IMPORT_ENTITY


@dataclass
class Flow:
    """An energy statistic and the statistic with its cost or compensation."""

    energy: str
    cost: str | None


@dataclass
class EnergySetup:
    """What the integration needs from the energy preferences."""

    has_grid: bool = False
    import_price: str | None = None
    export_price: str | None = None
    gas_price: str | None = None
    import_fixed: float | None = None
    export_fixed: float | None = None
    imports: list[Flow] = field(default_factory=list)
    exports: list[Flow] = field(default_factory=list)


def parse_prefs(
    prefs: dict[str, Any] | None, cost_sensors: dict[str, str] | None = None
) -> EnergySetup:
    """Collect price sensors and grid flows from the energy preferences."""
    setup = EnergySetup()
    cost_sensors = cost_sensors or {}

    def first(current: Any, value: Any) -> Any:
        return current if current is not None else value

    def fixed(current: float | None, value: Any) -> float | None:
        if current is None and isinstance(value, (int, float)):
            return float(value)
        return current

    for src in (prefs or {}).get("energy_sources") or []:
        if src.get("type") == "gas":
            setup.gas_price = first(setup.gas_price, src.get("entity_energy_price"))
            continue
        if src.get("type") != "grid":
            continue
        setup.has_grid = True
        # current schema
        setup.import_price = first(setup.import_price, src.get("entity_energy_price"))
        setup.export_price = first(
            setup.export_price, src.get("entity_energy_price_export")
        )
        setup.import_fixed = fixed(setup.import_fixed, src.get("number_energy_price"))
        setup.export_fixed = fixed(
            setup.export_fixed, src.get("number_energy_price_export")
        )
        if stat := src.get("stat_energy_from"):
            setup.imports.append(
                Flow(stat, src.get("stat_cost") or cost_sensors.get(stat))
            )
        if stat := src.get("stat_energy_to"):
            setup.exports.append(
                Flow(stat, src.get("stat_compensation") or cost_sensors.get(stat))
            )
        # older schema
        for flow in src.get("flow_from") or []:
            setup.import_price = first(
                setup.import_price, flow.get("entity_energy_price")
            )
            setup.import_fixed = fixed(
                setup.import_fixed, flow.get("number_energy_price")
            )
            if stat := flow.get("stat_energy_from"):
                setup.imports.append(
                    Flow(stat, flow.get("stat_cost") or cost_sensors.get(stat))
                )
        for flow in src.get("flow_to") or []:
            setup.export_price = first(
                setup.export_price, flow.get("entity_energy_price")
            )
            setup.export_fixed = fixed(
                setup.export_fixed, flow.get("number_energy_price")
            )
            if stat := flow.get("stat_energy_to"):
                setup.exports.append(
                    Flow(stat, flow.get("stat_compensation") or cost_sensors.get(stat))
                )
    return setup


def apply_overrides(setup: EnergySetup, options: dict[str, Any]) -> EnergySetup:
    """Use the price sensors from the options where they are set."""
    setup.import_price = options.get(CONF_IMPORT_ENTITY) or setup.import_price
    setup.export_price = options.get(CONF_EXPORT_ENTITY) or setup.export_price
    setup.gas_price = options.get(CONF_GAS_ENTITY) or setup.gas_price
    return setup


async def async_energy_setup(
    hass: HomeAssistant, options: dict[str, Any]
) -> EnergySetup | None:
    """Read the energy preferences; None when the energy integration is missing."""
    try:
        manager = await async_get_manager(hass)
    except Exception:  # noqa: BLE001 - the energy integration is optional
        return None
    cost_sensors = (hass.data.get("energy") or {}).get("cost_sensors") or {}
    return apply_overrides(parse_prefs(manager.data, cost_sensors), options)
