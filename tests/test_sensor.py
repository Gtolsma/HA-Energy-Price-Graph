"""Tests for the average price sensors."""

from datetime import timedelta

from freezegun.api import FrozenDateTimeFactory
from homeassistant.components.energy.data import async_get_manager
from homeassistant.components.recorder import Recorder
from homeassistant.components.recorder.models import StatisticMeanType
from homeassistant.components.recorder.statistics import async_import_statistics
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util
import pytest
from pytest_homeassistant_custom_component.components.recorder.common import (
    async_wait_recording_done,
)

from .test_init import _setup

PREFIX = "sensor.energy_price_graph_"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(recorder_mock, enable_custom_integrations):
    """Start the recorder before Home Assistant (overrides conftest)."""
    yield


def _import(hass: HomeAssistant, statistic_id: str, unit: str | None, rows) -> None:
    has_sum = "sum" in rows[0]
    async_import_statistics(
        hass,
        {
            "mean_type": StatisticMeanType.NONE
            if has_sum
            else StatisticMeanType.ARITHMETIC,
            "has_sum": has_sum,
            "name": None,
            "source": "recorder",
            "statistic_id": statistic_id,
            "unit_class": "energy" if unit == "kWh" else None,
            "unit_of_measurement": unit,
        },
        rows,
    )


async def test_sensors(
    recorder_mock: Recorder, hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    await hass.config.async_set_time_zone("Europe/Amsterdam")
    freezer.move_to("2026-09-28T16:30:00+02:00")
    today = dt_util.start_of_local_day()
    hour = [today + timedelta(hours=h) for h in (9, 10, 11, 12)]

    # Import: 1, 1 and 2 kWh at +0.30, -0.10 and +0.20 per kWh.
    _import(
        hass,
        "sensor.energy_in",
        "kWh",
        [
            {"start": hour[0], "sum": 0, "state": 0},
            {"start": hour[1], "sum": 1, "state": 1},
            {"start": hour[2], "sum": 2, "state": 2},
            {"start": hour[3], "sum": 4, "state": 4},
        ],
    )
    _import(
        hass,
        "sensor.cost_in",
        "EUR",
        [
            {"start": hour[0], "sum": 0, "state": 0},
            {"start": hour[1], "sum": 0.3, "state": 0.3},
            {"start": hour[2], "sum": 0.2, "state": 0.2},
            {"start": hour[3], "sum": 0.6, "state": 0.6},
        ],
    )
    _import(
        hass,
        "sensor.price",
        "EUR/kWh",
        [
            {"start": h, "mean": v, "min": v, "max": v}
            for h, v in zip(hour[1:], (0.3, -0.1, 0.2), strict=True)
        ],
    )
    # Export: 2 kWh for 0.10 in total, market price 0.08.
    _import(
        hass,
        "sensor.energy_out",
        "kWh",
        [
            {"start": hour[2], "sum": 0, "state": 0},
            {"start": hour[3], "sum": 2, "state": 2},
        ],
    )
    _import(
        hass,
        "sensor.comp_out",
        "EUR",
        [
            {"start": hour[2], "sum": 0, "state": 0},
            {"start": hour[3], "sum": 0.1, "state": 0.1},
        ],
    )
    _import(
        hass,
        "sensor.export_price",
        "EUR/kWh",
        [
            {"start": hour[3], "mean": 0.08, "min": 0.08, "max": 0.08},
        ],
    )
    await async_wait_recording_done(hass)

    manager = await async_get_manager(hass)
    await manager.async_update(
        {
            "energy_sources": [
                {
                    "type": "grid",
                    "flow_from": [
                        {
                            "stat_energy_from": "sensor.energy_in",
                            "stat_cost": "sensor.cost_in",
                            "entity_energy_price": "sensor.price",
                            "number_energy_price": None,
                        }
                    ],
                    "flow_to": [
                        {
                            "stat_energy_to": "sensor.energy_out",
                            "stat_compensation": "sensor.comp_out",
                            "entity_energy_price": "sensor.export_price",
                            "number_energy_price": None,
                        }
                    ],
                    "cost_adjustment_day": 0,
                }
            ]
        }
    )
    hass.config.currency = "EUR"
    await _setup(hass)

    def value(name: str) -> float:
        return float(hass.states.get(f"{PREFIX}{name}").state)

    assert abs(value("average_import_price_paid_today") - 0.15) < 1e-4
    assert abs(value("average_market_import_price_today") - 0.4 / 3) < 1e-4
    assert abs(value("average_export_price_received_today") - 0.05) < 1e-4
    assert abs(value("average_market_export_price_today") - 0.08) < 1e-4
    # Import (0.1333 - 0.15) x 4 + export (0.05 - 0.08) x 2
    assert abs(value("result_vs_market_today") - (-0.4 / 6 - 0.06)) < 1e-3
    assert abs(value("average_import_price_paid_this_month") - 0.15) < 1e-4

    state = hass.states.get(f"{PREFIX}result_vs_market_today")
    assert state.attributes["unit_of_measurement"] == "EUR"
    assert state.attributes["device_class"] == "monetary"
    assert state.attributes["last_reset"] == today.isoformat()
    price = hass.states.get(f"{PREFIX}average_import_price_paid_today")
    assert price.attributes["unit_of_measurement"] == "EUR/kWh"


async def test_sensors_without_energy_settings(
    recorder_mock: Recorder, hass: HomeAssistant
) -> None:
    await _setup(hass)
    state = hass.states.get(f"{PREFIX}average_import_price_paid_today")
    assert state is not None
    assert state.state == "unavailable"
