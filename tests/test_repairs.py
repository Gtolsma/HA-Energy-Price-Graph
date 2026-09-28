"""Tests for the repair issues."""

from homeassistant.components.energy.data import async_get_manager
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir

from .test_init import _setup

DOMAIN = "energy_price_graph"


async def _report(hass_ws_client, status: str, **extra) -> None:
    client = await hass_ws_client()
    await client.send_json_auto_id(
        {"type": f"{DOMAIN}/report", "status": status, **extra}
    )
    msg = await client.receive_json()
    assert msg["success"]


async def test_frontend_issue(hass: HomeAssistant, hass_ws_client) -> None:
    await _setup(hass)
    registry = ir.async_get(hass)

    await _report(hass_ws_client, "failed", view="electricity", error="TypeError: x")
    issue = registry.async_get_issue(DOMAIN, "frontend_not_active")
    assert issue is not None
    assert issue.translation_placeholders["error"] == "TypeError: x"

    await _report(hass_ws_client, "ok", view="electricity")
    assert registry.async_get_issue(DOMAIN, "frontend_not_active") is None

    await _report(hass_ws_client, "not_active")
    assert registry.async_get_issue(DOMAIN, "frontend_not_active") is not None


async def test_no_price_sensor_issue(hass: HomeAssistant) -> None:
    manager = await async_get_manager(hass)
    await manager.async_update(
        {
            "energy_sources": [
                {
                    "type": "grid",
                    "flow_from": [
                        {
                            "stat_energy_from": "sensor.in",
                            "stat_cost": None,
                            "entity_energy_price": None,
                            "number_energy_price": 0.3,
                        }
                    ],
                    "flow_to": [],
                    "cost_adjustment_day": 0,
                }
            ]
        }
    )
    await _setup(hass)
    registry = ir.async_get(hass)
    assert registry.async_get_issue(DOMAIN, "no_price_sensor") is not None

    # Adding a price sensor to the energy settings removes the issue.
    await manager.async_update(
        {
            "energy_sources": [
                {
                    "type": "grid",
                    "flow_from": [
                        {
                            "stat_energy_from": "sensor.in",
                            "stat_cost": None,
                            "entity_energy_price": "sensor.price",
                            "number_energy_price": None,
                        }
                    ],
                    "flow_to": [],
                    "cost_adjustment_day": 0,
                }
            ]
        }
    )
    await hass.async_block_till_done()
    assert registry.async_get_issue(DOMAIN, "no_price_sensor") is None


async def test_no_issue_without_grid(hass: HomeAssistant) -> None:
    await _setup(hass)
    assert ir.async_get(hass).async_get_issue(DOMAIN, "no_price_sensor") is None
