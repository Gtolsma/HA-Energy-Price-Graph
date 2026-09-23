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


async def test_setup_registers_module(hass: HomeAssistant, hass_client) -> None:
    entry = await _setup(hass)
    urls = _our_urls(hass)
    assert len(urls) == 1
    q = parse_qs(urlparse(urls[0]).query)
    assert q["period"] == ["auto"]
    assert q["views"] == ["electricity,overview"]
    assert q["export"] == ["1"]
    assert q["line"] == ["stepped"]

    client = await hass_client()
    resp = await client.get(urls[0])
    assert resp.status == 200
    body = await resp.text()
    assert "energy-view-strategy" in body

    # Only one instance allowed.
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "single_instance_allowed"

    # Unload removes the module URL.
    assert await hass.config_entries.async_unload(entry.entry_id)
    assert _our_urls(hass) == []


async def test_options_flow_updates_url(hass: HomeAssistant) -> None:
    entry = await _setup(hass)
    old = _our_urls(hass)[0]

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.FORM

    # No tabs selected -> error.
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            "period": "5minute",
            "line_style": "smooth",
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
            "line_style": "straight",
            "views": ["electricity"],
            "show_export": False,
            "minmax": True,
            "title": "Prijs",
            "import_entity": "sensor.price",
        },
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()

    urls = _our_urls(hass)
    assert len(urls) == 1 and urls[0] != old
    q = parse_qs(urlparse(urls[0]).query)
    assert q["period"] == ["5minute"]
    assert q["views"] == ["electricity"]
    assert q["export"] == ["0"]
    assert q["minmax"] == ["1"]
    assert q["title"] == ["Prijs"]
    assert q["line"] == ["straight"]
    assert q["entity"] == ["sensor.price"]
