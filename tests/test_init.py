"""Tests for setup, options and the served frontend module."""

from urllib.parse import parse_qs, urlparse

from homeassistant import config_entries
from homeassistant.components.frontend import DATA_EXTRA_MODULE_URL
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.setup import async_setup_component

DOMAIN = "energy_price_graph"


def _our_urls(hass: HomeAssistant) -> list[str]:
    return [u for u in hass.data[DATA_EXTRA_MODULE_URL].urls if DOMAIN in u]


async def _setup(hass: HomeAssistant):
    assert await async_setup_component(hass, "frontend", {})
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    return result["result"]


async def _ws_options(hass_ws_client) -> dict | None:
    client = await hass_ws_client()
    await client.send_json_auto_id({"type": f"{DOMAIN}/options"})
    msg = await client.receive_json()
    assert msg["success"]
    return msg["result"]["options"]


async def test_setup_registers_module(
    hass: HomeAssistant, hass_client, hass_ws_client
) -> None:
    entry = await _setup(hass)
    urls = _our_urls(hass)
    assert len(urls) == 1
    # Only the version is in the URL; options come over the websocket API.
    assert set(parse_qs(urlparse(urls[0]).query)) == {"v"}

    client = await hass_client()
    resp = await client.get(urls[0])
    assert resp.status == 200
    assert "energy-view-strategy" in await resp.text()

    options = await _ws_options(hass_ws_client)
    assert options["period"] == "auto"
    assert options["line_style"] == "straight"
    assert options["views"] == ["electricity", "overview"]
    assert options["show_export"] is True
    assert options["show_current"] is True
    assert options["show_average"] is True

    # Only one instance allowed.
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "single_instance_allowed"

    # Unload removes the module URL and the options.
    assert await hass.config_entries.async_unload(entry.entry_id)
    assert _our_urls(hass) == []
    assert await _ws_options(hass_ws_client) is None


async def test_options_flow_updates_options(
    hass: HomeAssistant, hass_ws_client
) -> None:
    entry = await _setup(hass)
    url = _our_urls(hass)[0]

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.FORM

    # No tabs selected -> error.
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            "period": "5minute",
            "line_style": "smooth",
            "show_current": True,
            "show_average": True,
            "views": [],
            "show_export": False,
            "minmax": True,
        },
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"views": "no_views"}

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            "period": "5minute",
            "line_style": "stepped",
            "show_current": False,
            "show_average": False,
            "views": ["electricity"],
            "show_export": False,
            "minmax": True,
            "title": "Prijs",
            "import_entity": "sensor.price",
        },
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()

    # The module URL stays the same, so no browser refresh is needed ...
    assert _our_urls(hass) == [url]
    # ... and the new options are served over the websocket API.
    options = await _ws_options(hass_ws_client)
    assert options["period"] == "5minute"
    assert options["line_style"] == "stepped"
    assert options["show_current"] is False
    assert options["show_average"] is False
    assert options["views"] == ["electricity"]
    assert options["show_export"] is False
    assert options["minmax"] is True
    assert options["title"] == "Prijs"
    assert options["import_entity"] == "sensor.price"
