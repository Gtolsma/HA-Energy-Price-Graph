"""Tests for the diagnostics."""

from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.components.diagnostics import (
    get_diagnostics_for_config_entry,
)

from .test_init import _setup


async def test_diagnostics(hass: HomeAssistant, hass_client, hass_ws_client) -> None:
    assert await async_setup_component(hass, "diagnostics", {})
    entry = await _setup(hass)
    hass.states.async_set(
        "sensor.price",
        "0.25",
        {
            "unit_of_measurement": "EUR/kWh",
            "raw_today": [],
            "state_class": "measurement",
        },
    )

    client = await hass_ws_client()
    await client.send_json_auto_id(
        {"type": "energy_price_graph/report", "status": "ok", "view": "electricity"}
    )
    assert (await client.receive_json())["success"]

    hass.config_entries.async_update_entry(
        entry, options={"import_entity": "sensor.price"}
    )
    result = await get_diagnostics_for_config_entry(hass, hass_client, entry)
    assert result["options"]["period"] == "auto_fine"
    assert result["version"]
    assert result["price_sensors"]["import"] == {
        "entity_id": "sensor.price",
        "state": "0.25",
        "unit_of_measurement": "EUR/kWh",
        "state_class": "measurement",
        "attributes": ["raw_today", "state_class", "unit_of_measurement"],
    }
    assert result["frontend_reports"]["ok"]["view"] == "electricity"
