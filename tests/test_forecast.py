"""Tests for upcoming prices from price integrations' actions."""

from typing import Any

from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.energy_price_graph.forecast import async_get_forecast

from .test_init import _setup

DOMAIN = "energy_price_graph"


def _register(hass: HomeAssistant, domain: str, service: str, handler) -> list:
    calls: list[dict[str, Any]] = []

    async def _handle(call: ServiceCall) -> dict[str, Any]:
        calls.append(dict(call.data))
        return handler(call)

    hass.services.async_register(
        domain, service, _handle, supports_response=SupportsResponse.ONLY
    )
    return calls


def _entity(hass: HomeAssistant, platform: str, unique_id: str, entry) -> str:
    return (
        er.async_get(hass)
        .async_get_or_create(
            "sensor",
            platform,
            unique_id,
            config_entry=entry,
            suggested_object_id=unique_id,
        )
        .entity_id
    )


async def test_nordpool(hass: HomeAssistant) -> None:
    entry = MockConfigEntry(domain="nordpool", data={"areas": ["SE3", "NL"]})
    entry.add_to_hass(hass)
    entity_id = _entity(hass, "nordpool", "NL-current_price", entry)

    def handler(call: ServiceCall) -> dict[str, Any]:
        if call.data["date"].endswith("-01"):  # "tomorrow" not published yet
            raise ServiceValidationError("no data")
        return {
            "NL": [
                {
                    "start": f"{call.data['date']}T10:00:00+00:00",
                    "end": "x",
                    "price": 95.5,
                },
                {
                    "start": f"{call.data['date']}T11:00:00+00:00",
                    "end": "x",
                    "price": 101,
                },
            ]
        }

    calls = _register(hass, "nordpool", "get_prices_for_date", handler)
    result = await async_get_forecast(hass, entity_id)
    assert result["source"] == "nordpool"
    assert calls[0]["areas"] == ["NL"]
    assert calls[0]["config_entry"] == entry.entry_id
    assert [p[1] for p in result["points"]][:2] == [95.5, 101]
    assert result["points"][0][0].endswith("+00:00")

    # Cached: no new calls.
    await async_get_forecast(hass, entity_id)
    assert len(calls) == 2


async def test_energyzero_gas_and_easyenergy_return(hass: HomeAssistant) -> None:
    ez = MockConfigEntry(domain="energyzero")
    ez.add_to_hass(hass)
    ee = MockConfigEntry(domain="easyenergy")
    ee.add_to_hass(hass)
    gas = _entity(hass, "energyzero", f"{ez.entry_id}_today_gas_current_hour_price", ez)
    ret = _entity(
        hass, "easyenergy", f"{ee.entry_id}_today_energy_return_current_hour_price", ee
    )
    prices = {"prices": [{"timestamp": "2026-09-28 10:00:00+00:00", "price": 1.2}]}
    ez_calls = _register(hass, "energyzero", "get_gas_prices", lambda c: prices)
    ee_calls = _register(
        hass, "easyenergy", "get_energy_return_prices", lambda c: prices
    )

    result = await async_get_forecast(hass, gas)
    assert result == {
        "source": "energyzero",
        "points": [["2026-09-28T10:00:00+00:00", 1.2]],
    }
    assert ez_calls[0]["incl_vat"] is True
    assert (await async_get_forecast(hass, ret))["source"] == "easyenergy"
    assert ee_calls[0]["config_entry"] == ee.entry_id


async def test_tibber(hass: HomeAssistant) -> None:
    entry = MockConfigEntry(domain="tibber")
    entry.add_to_hass(hass)
    entity_id = _entity(hass, "tibber", "home_id", entry)
    _register(
        hass,
        "tibber",
        "get_prices",
        lambda c: {
            "prices": {
                "Home": [{"start_time": "2026-09-28T10:00:00+02:00", "price": 0.31}]
            }
        },
    )
    result = await async_get_forecast(hass, entity_id)
    assert result["points"] == [["2026-09-28T10:00:00+02:00", 0.31]]


async def test_unknown_or_missing_integration(hass: HomeAssistant) -> None:
    assert await async_get_forecast(hass, "sensor.unknown") == {
        "source": None,
        "points": [],
    }
    entry = MockConfigEntry(domain="nordpool", data={"areas": ["NL"]})
    entry.add_to_hass(hass)
    # Registered entity but the integration's action does not exist.
    entity_id = _entity(hass, "nordpool", "NL-current_price", entry)
    assert (await async_get_forecast(hass, entity_id))["points"] == []


async def test_failing_action_gives_no_points(hass: HomeAssistant) -> None:
    entry = MockConfigEntry(domain="tibber")
    entry.add_to_hass(hass)
    entity_id = _entity(hass, "tibber", "home_id", entry)

    def handler(call: ServiceCall) -> dict[str, Any]:
        raise ValueError("boom")

    _register(hass, "tibber", "get_prices", handler)
    assert (await async_get_forecast(hass, entity_id))["points"] == []


async def test_websocket_command(hass: HomeAssistant, hass_ws_client) -> None:
    await _setup(hass)
    client = await hass_ws_client()
    await client.send_json_auto_id(
        {"type": f"{DOMAIN}/forecast", "entity_id": "sensor.unknown"}
    )
    msg = await client.receive_json()
    assert msg["success"]
    assert msg["result"] == {"source": None, "points": []}
