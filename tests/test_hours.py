"""Tests for the cheapest / most expensive hours and their sensors."""

from datetime import datetime, timedelta

from freezegun.api import FrozenDateTimeFactory
from homeassistant.components.energy.data import async_get_manager
from homeassistant.core import HomeAssistant, State
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import async_fire_time_changed

from custom_components.energy_price_graph.hours import (
    RETRY_INTERVAL,
    UPDATE_INTERVAL,
    HoursCoordinator,
    HoursData,
    attribute_points,
    calculate,
    cheapest_block,
    extreme_hours,
    forecast_scale,
    hourly,
    periods,
)

from .test_init import _setup

TZ = "Europe/Amsterdam"


def _day(start: datetime, prices: list[float]) -> dict[datetime, float]:
    return {start + timedelta(hours=i): p for i, p in enumerate(prices)}


def _state(**attributes) -> State:
    return State("sensor.price", "0.25", attributes)


# --------------------------------------------------------------------------
# Reading prices from attributes
# --------------------------------------------------------------------------


def test_attribute_points_nord_pool_and_entsoe() -> None:
    nordpool = _state(
        raw_today=[
            {"start": "2026-09-28T00:00:00+02:00", "end": "x", "value": 0.2},
            {"start": "2026-09-28T01:00:00+02:00", "end": "x", "value": 0.1},
        ]
    )
    points = attribute_points(nordpool)
    assert [p for _, p in points] == [0.2, 0.1]
    assert points[0][0] == dt_util.parse_datetime("2026-09-28T00:00:00+02:00")

    entsoe = _state(prices=[{"time": "2026-09-28T00:00:00+02:00", "price": 0.3}])
    assert [p for _, p in attribute_points(entsoe)] == [0.3]


def test_attribute_points_unknown_fields() -> None:
    # One other number: that is the price.
    single = _state(data=[{"from": "2026-09-28T00:00:00+02:00", "cost": 0.4}])
    assert [p for _, p in attribute_points(single)] == [0.4]
    # Two other numbers: no guessing ...
    double = _state(
        data=[{"from": "2026-09-28T00:00:00+02:00", "cost": 0.4, "index": 3}]
    )
    assert attribute_points(double) == []
    # ... unless the field is named in the options.
    assert [p for _, p in attribute_points(double, value_key="cost")] == [0.4]
    # Only the chosen attribute is read.
    both = _state(
        a=[{"start": "2026-09-28T00:00:00+02:00", "value": 1.0}],
        b=[{"start": "2026-09-28T01:00:00+02:00", "value": 2.0}],
    )
    assert [p for _, p in attribute_points(both, attribute="b")] == [2.0]
    assert attribute_points(None) == []


async def test_hourly_averages_quarters(hass: HomeAssistant) -> None:
    await hass.config.async_set_time_zone(TZ)
    start = dt_util.parse_datetime("2026-09-28T10:00:00+02:00")
    quarters = [
        (start + timedelta(minutes=15 * i), v) for i, v in enumerate((1, 2, 3, 6))
    ]
    assert hourly(quarters) == {start: 3.0}


# --------------------------------------------------------------------------
# Choosing the hours
# --------------------------------------------------------------------------

START = datetime(2026, 9, 28)


def test_extreme_hours_per_day() -> None:
    prices = _day(START, [0.3] * 24)
    prices[START + timedelta(hours=3)] = 0.1
    prices[START + timedelta(hours=19)] = 0.6
    assert extreme_hours(prices, 1) == {START + timedelta(hours=3)}
    assert extreme_hours(prices, 1, expensive=True) == {START + timedelta(hours=19)}
    assert extreme_hours(prices, 0) == set()


def test_incomplete_days_are_skipped() -> None:
    prices = _day(START, [0.3] * 24) | _day(START + timedelta(days=1), [0.1] * 10)
    hours = extreme_hours(prices, 2)
    assert all(h.date() == START.date() for h in hours)


def test_cheapest_and_most_expensive_never_overlap() -> None:
    prices = _day(START, [0.1] * 12 + [0.2] * 12)
    cheap, dear = calculate(prices, 12, 13)
    assert len(cheap) == 12
    assert len(dear) == 12
    assert not set(cheap) & set(dear)


def test_periods_and_next_start() -> None:
    hours = [START + timedelta(hours=h) for h in (2, 3, 4, 13, 22, 23)]
    assert periods(hours) == [
        (START + timedelta(hours=2), START + timedelta(hours=5)),
        (START + timedelta(hours=13), START + timedelta(hours=14)),
        (START + timedelta(hours=22), START + timedelta(hours=24)),
    ]
    data = HoursData(cheapest=hours)
    # During the first run, the next one is the run after it.
    assert data.next_start("cheapest", START + timedelta(hours=3)) == START + timedelta(
        hours=13
    )
    assert data.next_start("cheapest", START + timedelta(hours=23)) is None
    assert data.next_start("expensive", START) is None


# --------------------------------------------------------------------------
# Sensors
# --------------------------------------------------------------------------

PRICES = [0.30] * 24
for _h, _p in ((13, 0.05), (14, 0.02), (15, 0.08), (19, 0.60), (20, 0.55)):
    PRICES[_h] = _p


async def _prepare(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory | None = None
) -> None:
    await hass.config.async_set_time_zone(TZ)
    if freezer:
        freezer.move_to("2026-09-28T10:30:00+02:00")
    today = dt_util.start_of_local_day()
    hass.states.async_set(
        "sensor.price",
        "0.30",
        {
            "unit_of_measurement": "EUR/kWh",
            "raw_today": [
                {"start": (today + timedelta(hours=h)).isoformat(), "value": p}
                for h, p in enumerate(PRICES)
            ],
        },
    )
    manager = await async_get_manager(hass)
    await manager.async_update(
        {
            "energy_sources": [
                {
                    "type": "grid",
                    "flow_from": [
                        {
                            "stat_energy_from": "sensor.energy_in",
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


async def _with_hours(
    hass: HomeAssistant, cheapest: int, expensive: int, block: int = 0
):
    entry = await _setup(hass)
    hass.config_entries.async_update_entry(
        entry,
        options={
            **entry.options,
            "cheapest_hours": cheapest,
            "expensive_hours": expensive,
            "block_hours": block,
        },
    )
    await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def test_hour_sensors(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    await _prepare(hass, freezer)
    await _with_hours(hass, 3, 2)
    today = dt_util.start_of_local_day()

    cheap = hass.states.get("binary_sensor.energy_price_graph_cheapest_hours_now")
    dear = hass.states.get("binary_sensor.energy_price_graph_most_expensive_hours_now")
    assert cheap.state == "off"
    assert dear.state == "off"
    assert cheap.attributes["hours_per_day"] == 3
    assert cheap.attributes["today"] == [
        (today + timedelta(hours=h)).isoformat() for h in (13, 14, 15)
    ]
    assert cheap.attributes["tomorrow"] == []
    assert cheap.attributes["periods"] == [
        {
            "start": (today + timedelta(hours=13)).isoformat(),
            "end": (today + timedelta(hours=16)).isoformat(),
        }
    ]
    assert dear.attributes["today"] == [
        (today + timedelta(hours=h)).isoformat() for h in (19, 20)
    ]

    next_cheap = hass.states.get("sensor.energy_price_graph_next_cheapest_hours")
    assert dt_util.parse_datetime(next_cheap.state) == today + timedelta(hours=13)
    assert next_cheap.attributes["device_class"] == "timestamp"

    # At 13:00 the binary sensor turns on without waiting for an update.
    freezer.move_to(today + timedelta(hours=13))
    async_fire_time_changed(hass, today + timedelta(hours=13))
    await hass.async_block_till_done()
    cheap = hass.states.get("binary_sensor.energy_price_graph_cheapest_hours_now")
    assert cheap.state == "on"
    # The next cheap period has not started yet: unknown until tomorrow.
    next_cheap = hass.states.get("sensor.energy_price_graph_next_cheapest_hours")
    assert next_cheap.state == "unknown"


async def test_hour_sensors_off_by_default(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    await _prepare(hass, freezer)
    await _setup(hass)
    for entity_id in (
        "binary_sensor.energy_price_graph_cheapest_hours_now",
        "binary_sensor.energy_price_graph_most_expensive_hours_now",
        "sensor.energy_price_graph_next_cheapest_hours",
        "sensor.energy_price_graph_next_most_expensive_hours",
    ):
        assert hass.states.get(entity_id).state == "unavailable"


async def test_hour_sensors_without_prices(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    await hass.config.async_set_time_zone(TZ)
    freezer.move_to("2026-09-28T10:30:00+02:00")
    # A price sensor without upcoming prices: no hours to choose from.
    hass.states.async_set("sensor.price", "0.30")
    await _with_hours(hass, 3, 0)
    state = hass.states.get("binary_sensor.energy_price_graph_cheapest_hours_now")
    assert state.state == "unavailable"


async def test_hours_over_websocket(hass: HomeAssistant, hass_ws_client) -> None:
    """The hours card gets the same hours as the sensors."""
    await _prepare(hass)
    await _with_hours(hass, 3, 2)
    client = await hass_ws_client()
    await client.send_json_auto_id({"type": "energy_price_graph/hours"})
    result = (await client.receive_json())["result"]
    assert result["cheapest_count"] == 3
    assert result["expensive_count"] == 2
    assert result["source"] == "sensor.price"
    today = dt_util.start_of_local_day()
    assert result["cheapest"] == [
        (today + timedelta(hours=h)).isoformat() for h in (13, 14, 15)
    ]
    assert result["expensive"] == [
        (today + timedelta(hours=h)).isoformat() for h in (19, 20)
    ]


async def test_hours_follow_the_price_sensor(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """Right after a restart the sensor may not have its prices yet."""
    await _prepare(hass, freezer)
    full = hass.states.get("sensor.price")
    # The sensor is there, but without the upcoming prices.
    hass.states.async_set("sensor.price", "0.30", {"unit_of_measurement": "EUR/kWh"})
    entry = await _with_hours(hass, 3, 2)
    hours = entry.runtime_data.hours
    entity_id = "binary_sensor.energy_price_graph_cheapest_hours_now"
    assert hass.states.get(entity_id).state == "unavailable"
    assert hours.update_interval == RETRY_INTERVAL

    # As soon as the prices arrive, the hours are calculated, without waiting.
    hass.states.async_set("sensor.price", "0.30", dict(full.attributes))
    await hass.async_block_till_done()
    assert hass.states.get(entity_id).state != "unavailable"
    assert hours.data.cheapest
    assert hours.update_interval == UPDATE_INTERVAL

    # Other changes of the sensor (its price) do not trigger a calculation.
    calls = 0
    original = hours._async_update_data

    async def counted():
        nonlocal calls
        calls += 1
        return await original()

    hours._async_update_data = counted
    hass.states.async_set("sensor.price", "0.31", dict(full.attributes))
    await hass.async_block_till_done()
    assert calls == 0


def test_forecast_scale() -> None:
    start = datetime(2026, 9, 28)
    # Prices in cents or per MWh are brought to the unit of the sensor (EUR/kWh).
    cents = [(start, 30.0), (start + timedelta(hours=1), 35.0)]
    mwh = [(start, 300.0), (start + timedelta(hours=1), 350.0)]
    assert forecast_scale(cents, 0.31) == 0.01
    assert forecast_scale(mwh, 0.31) == 0.001
    assert forecast_scale([(start, 0.3)], 0.31) == 1.0
    # Without a current price or prices there is nothing to compare with.
    assert forecast_scale(cents, None) == 1.0
    assert forecast_scale([], 0.31) == 1.0


async def test_passed_hours_come_from_the_recorder(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, monkeypatch
) -> None:
    """Integrations that only list the upcoming prices still give a whole day."""
    await _prepare(hass, freezer)
    today = dt_util.start_of_local_day()
    # Only the upcoming prices (from 11:00) ...
    state = hass.states.get("sensor.price")
    upcoming = [
        item
        for item in state.attributes["raw_today"]
        if dt_util.parse_datetime(item["start"]) >= today + timedelta(hours=11)
    ]
    hass.states.async_set(
        "sensor.price", "0.30", {**state.attributes, "raw_today": upcoming}
    )

    # ... and the hours before that from the recorded prices, with a cheap one.
    async def recorded(self, entity_id: str):
        assert entity_id == "sensor.price"
        return [
            (today + timedelta(hours=h), 0.01 if h == 3 else 0.3) for h in range(11)
        ]

    monkeypatch.setattr(HoursCoordinator, "_recorded", recorded)
    entry = await _with_hours(hass, 3, 0)
    hours = entry.runtime_data.hours
    assert hours.data.cheapest == [today + timedelta(hours=h) for h in (3, 13, 14)]
    assert hours.data.reason is None


async def test_reason_when_there_are_no_hours(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    await _prepare(hass, freezer)
    # A price sensor without upcoming prices (and nothing recorded).
    hass.states.async_set("sensor.price", "0.30", {"unit_of_measurement": "EUR/kWh"})
    entry = await _with_hours(hass, 3, 0)
    assert entry.runtime_data.hours.data.reason == "no_prices"
    assert entry.runtime_data.hours.data.as_dict()["reason"] == "no_prices"

    # Without a source for upcoming prices (switched off in the options).
    hass.config_entries.async_update_entry(
        entry, options={**entry.options, "forecast_auto": False}
    )
    await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.runtime_data.hours.data.reason == "no_source"


def test_cheapest_block() -> None:
    start = datetime(2026, 9, 28, tzinfo=dt_util.get_default_time_zone())
    prices = _day(start, [5, 5, 1, 1, 6, 2, 2, 2, 9])
    # Cheapest run of 2 hours in a row: hours 2 and 3 (not the single cheap ones).
    assert cheapest_block(prices, 2, start) == (start + timedelta(hours=2), 1.0)
    assert cheapest_block(prices, 3, start) == (start + timedelta(hours=5), 2.0)
    # Runs that are over are skipped: from 04:30 on the run 2-3 can not be used.
    since = start + timedelta(hours=4, minutes=30)
    assert cheapest_block(prices, 2, since) == (start + timedelta(hours=5), 2.0)
    # A run in progress still counts.
    since = start + timedelta(hours=2, minutes=30)
    assert cheapest_block(prices, 2, since) == (start + timedelta(hours=2), 1.0)
    # A gap in the prices breaks a run; off or too long gives nothing.
    gap = {h: p for h, p in prices.items() if h != start + timedelta(hours=3)}
    assert cheapest_block(gap, 2, start) == (start + timedelta(hours=5), 2.0)
    assert cheapest_block(prices, 0, start) is None
    assert cheapest_block(prices, 12, start) is None


async def test_cheapest_block_sensor(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    await _prepare(hass, freezer)
    entry = await _with_hours(hass, 0, 0, block=3)
    data = entry.runtime_data.hours.data
    assert data.block_start is not None
    assert data.block_end == data.block_start + timedelta(hours=3)
    assert data.as_dict()["block_start"] == data.block_start.isoformat()
    state = hass.states.get("sensor.energy_price_graph_cheapest_block_start")
    assert state.state == dt_util.as_utc(data.block_start).isoformat()
    assert state.attributes["hours"] == 3
    assert state.attributes["end"] == data.block_end.isoformat()
    assert state.attributes["average_price"] is not None

    # Switched off: no block, sensor unavailable.
    hass.config_entries.async_update_entry(
        entry, options={**entry.options, "cheapest_hours": 3, "block_hours": 0}
    )
    await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    state = hass.states.get("sensor.energy_price_graph_cheapest_block_start")
    assert state.state == "unavailable"
