"""The cheapest and the most expensive hours of each day.

The same hours as the green and orange bands in the price graph, for the
binary sensors, the "next" sensors and the hours card. The prices come from
the attributes of the price sensor (or the chosen forecast sensor), or from
the action of its integration, like the upcoming prices in the graph. Only
the order of the prices matters, so they are not scaled.
"""

from __future__ import annotations

from collections.abc import Iterable
import contextlib
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import logging
import math
from typing import TYPE_CHECKING, Any

from homeassistant.components.recorder import get_instance
from homeassistant.components.recorder.statistics import statistics_during_period
from homeassistant.core import (
    CALLBACK_TYPE,
    Event,
    EventStateChangedData,
    HomeAssistant,
    State,
    callback,
)
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .const import (
    CONF_BLOCK_HOURS,
    CONF_CHEAPEST_HOURS,
    CONF_EXPENSIVE_HOURS,
    CONF_FORECAST_ATTRIBUTE,
    CONF_FORECAST_AUTO,
    CONF_FORECAST_IMPORT_ENTITY,
    CONF_FORECAST_VALUE_KEY,
    DEFAULT_OPTIONS,
    DOMAIN,
)
from .forecast import async_get_forecast
from .prefs import async_energy_setup

if TYPE_CHECKING:
    from . import EnergyPriceGraphConfigEntry

_LOGGER = logging.getLogger(__name__)

UPDATE_INTERVAL = timedelta(minutes=15)
# Without hours (for example right after a restart, before the price integration
# has its upcoming prices) look again sooner.
RETRY_INTERVAL = timedelta(minutes=1)
# A day counts once (almost) all of its hours are known, as in the graph.
MIN_HOURS = 20

# Same keys as the frontend module (forecastPoints).
TIME_KEYS = [
    "start",
    "from",
    "time",
    "datetime",
    "date_time",
    "start_time",
    "startsAt",
    "starts_at",
    "valid_from",
    "date",
    "timestamp",
]
END_KEYS = ["end", "till", "to", "end_time", "endsAt", "ends_at", "valid_till"]
VALUE_KEYS = [
    "value",
    "price",
    "total",
    "electricity_price",
    "price_eur",
    "marketPrice",
    "market_price",
    "price_incl_vat",
    "energy_price",
    "gas_price",
]

Points = list[tuple[datetime, float]]


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _timestamp(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        ts = value
    elif isinstance(value, str):
        ts = dt_util.parse_datetime(value)
    elif _is_number(value):
        # Seconds or milliseconds since the epoch.
        ts = dt_util.utc_from_timestamp(value / 1000 if value > 1e11 else value)
    else:
        return None
    if ts is None:
        return None
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=dt_util.get_default_time_zone())
    return ts


def _price_key(item: dict[str, Any], value_key: str | None) -> str | None:
    """The field with the price in an item, or None."""
    if value_key:
        return value_key if _is_number(item.get(value_key)) else None
    if key := next((k for k in VALUE_KEYS if _is_number(item.get(k))), None):
        return key
    skip = set(TIME_KEYS) | set(END_KEYS)
    others = [k for k, v in item.items() if k not in skip and _is_number(v)]
    return others[0] if len(others) == 1 else None


def attribute_points(
    state: State | None, attribute: str | None = None, value_key: str | None = None
) -> Points:
    """Prices from the attributes of a sensor, like the frontend module.

    Without a known price field, a field is only used when it is the only
    other number in the item, so an unrelated number is never taken as a price.
    """
    if state is None:
        return []
    points: dict[datetime, float] = {}

    def visit(value: Any, depth: int) -> None:
        if depth > 2 or not value:
            return
        if isinstance(value, dict):
            for v in value.values():
                visit(v, depth + 1)
            return
        if not isinstance(value, list):
            return
        for item in value:
            if not isinstance(item, dict):
                continue
            t_key = next((k for k in TIME_KEYS if item.get(k) is not None), None)
            ts = _timestamp(item[t_key]) if t_key else None
            if ts is not None and (v_key := _price_key(item, value_key)):
                points[ts] = float(item[v_key])

    attrs = state.attributes
    sources = [attrs.get(attribute)] if attribute else list(attrs.values())
    for value in sources:
        visit(value, 0)
    return sorted(points.items())


def hourly(points: Iterable[tuple[datetime, float]]) -> dict[datetime, float]:
    """Average price per hour (start of the hour, local time)."""
    sums: dict[datetime, list[float]] = {}
    for ts, value in points:
        local = dt_util.as_local(ts)
        hour = local.replace(minute=0, second=0, microsecond=0)
        sums.setdefault(hour, []).append(value)
    return {h: sum(v) / len(v) for h, v in sums.items()}


def forecast_scale(points: Points, reference: float | None) -> float:
    """The factor (1, ct, MWh, ...) that brings the points to the unit of the sensor.

    Like the frontend module: the one that puts the median closest to the
    current price. Needed to combine upcoming prices with recorded prices.
    """
    values = sorted(abs(value) for _, value in points if value)
    if not values or not reference:
        return 1.0
    median = values[len(values) // 2]
    return min(
        (1.0, 0.01, 0.001, 1e-5, 1e-7),
        key=lambda f: abs(math.log10(median * f / abs(reference))),
    )


def extreme_hours(
    prices: dict[datetime, float],
    count: int,
    *,
    expensive: bool = False,
    exclude: set[datetime] | None = None,
) -> set[datetime]:
    """The `count` cheapest (or most expensive) hours of each complete day."""
    out: set[datetime] = set()
    if count <= 0:
        return out
    exclude = exclude or set()
    days: dict[Any, list[tuple[datetime, float]]] = {}
    for hour, price in prices.items():
        days.setdefault(hour.date(), []).append((hour, price))
    for hours in days.values():
        if len(hours) < MIN_HOURS:
            continue
        candidates = [h for h in hours if h[0] not in exclude]
        candidates.sort(key=lambda h: h[1], reverse=expensive)
        out.update(h for h, _ in candidates[:count])
    return out


def periods(hours: Iterable[datetime]) -> list[tuple[datetime, datetime]]:
    """Runs of consecutive hours as (start, end)."""
    out: list[tuple[datetime, datetime]] = []
    for hour in sorted(hours):
        if out and out[-1][1] == hour:
            out[-1] = (out[-1][0], hour + timedelta(hours=1))
        else:
            out.append((hour, hour + timedelta(hours=1)))
    return out


def block_starts(hours: Iterable[datetime]) -> list[datetime]:
    """Start of each run of consecutive hours."""
    return [start for start, _ in periods(hours)]


def cheapest_block(
    prices: dict[datetime, float], count: int, since: datetime
) -> tuple[datetime, float] | None:
    """Start and average price of the cheapest run of `count` consecutive hours.

    Only runs that end after `since` and lie completely in the known prices are
    considered; the earliest one wins a tie.
    """
    if count <= 0:
        return None
    step = timedelta(hours=1)
    best: tuple[float, datetime] | None = None
    for start in sorted(prices):
        if start + count * step <= since:
            continue
        run = [start + i * step for i in range(count)]
        if not all(hour in prices for hour in run):
            continue
        total = sum(prices[hour] for hour in run)
        if best is None or total < best[0] - 1e-12:
            best = (total, start)
    if best is None:
        return None
    return best[1], best[0] / count


@dataclass
class HoursData:
    """The cheapest and most expensive hours that are known."""

    source: str | None = None
    cheapest: list[datetime] = field(default_factory=list)
    expensive: list[datetime] = field(default_factory=list)
    cheapest_count: int = 0
    expensive_count: int = 0
    # The cheapest run of `block_count` consecutive hours that is still to come.
    block_count: int = 0
    block_start: datetime | None = None
    block_average: float | None = None
    # Why there are no hours: "no_source" (no price sensor to take the prices
    # from) or "no_prices" (the sensor gives no upcoming prices).
    reason: str | None = None

    def hours(self, kind: str) -> list[datetime]:
        """The hours of one kind ("cheapest" or "expensive")."""
        return self.cheapest if kind == "cheapest" else self.expensive

    def is_on(self, kind: str, now: datetime | None = None) -> bool:
        """Whether the current hour is one of them."""
        now = dt_util.as_local(now or dt_util.now())
        hour = now.replace(minute=0, second=0, microsecond=0)
        return hour in self.hours(kind)

    def next_start(self, kind: str, now: datetime | None = None) -> datetime | None:
        """Start of the next run of these hours that has not started yet."""
        now = now or dt_util.now()
        return next((s for s in block_starts(self.hours(kind)) if s > now), None)

    @property
    def block_end(self) -> datetime | None:
        """End of the cheapest block."""
        if self.block_start is None:
            return None
        return self.block_start + timedelta(hours=self.block_count)

    def as_dict(self) -> dict[str, Any]:
        """For the websocket API (the hours card)."""
        return {
            "source": self.source,
            "cheapest": [h.isoformat() for h in self.cheapest],
            "expensive": [h.isoformat() for h in self.expensive],
            "cheapest_count": self.cheapest_count,
            "expensive_count": self.expensive_count,
            "block_count": self.block_count,
            "block_start": self.block_start.isoformat() if self.block_start else None,
            "reason": self.reason,
        }


def calculate(
    prices: dict[datetime, float], cheapest: int, expensive: int
) -> tuple[list[datetime], list[datetime]]:
    """Cheapest and most expensive hours; an hour is never both."""
    cheap = extreme_hours(prices, cheapest)
    dear = extreme_hours(prices, expensive, expensive=True, exclude=cheap)
    return sorted(cheap), sorted(dear)


class HoursCoordinator(DataUpdateCoordinator[HoursData]):
    """Find the cheapest and most expensive hours of today and tomorrow."""

    def __init__(self, hass: HomeAssistant, entry: EnergyPriceGraphConfigEntry) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=f"{DOMAIN}_hours",
            update_interval=UPDATE_INTERVAL,
        )
        self.options = {**DEFAULT_OPTIONS, **entry.options}
        self._tracked: str | None = None
        self._unsub_source: CALLBACK_TYPE | None = None

    async def async_shutdown(self) -> None:
        """Stop listening to the price sensor and stop updating."""
        self._track(None)
        await super().async_shutdown()

    def _track(self, entity_id: str | None) -> None:
        """Listen to the price sensor, so new upcoming prices are used at once."""
        if entity_id == self._tracked:
            return
        if self._unsub_source:
            self._unsub_source()
            self._unsub_source = None
        self._tracked = entity_id
        if entity_id:
            self._unsub_source = async_track_state_change_event(
                self.hass, [entity_id], self._source_changed
            )

    @callback
    def _source_changed(self, event: Event[EventStateChangedData]) -> None:
        """Calculate again when the upcoming prices of the sensor changed."""
        old, new = event.data["old_state"], event.data["new_state"]
        if new is None or (old is not None and old.attributes == new.attributes):
            return
        self.hass.async_create_task(self.async_request_refresh())

    @property
    def cheapest_count(self) -> int:
        """Number of cheapest hours per day (0 = off)."""
        return int(self.options.get(CONF_CHEAPEST_HOURS) or 0)

    @property
    def expensive_count(self) -> int:
        """Number of most expensive hours per day (0 = off)."""
        return int(self.options.get(CONF_EXPENSIVE_HOURS) or 0)

    @property
    def block_count(self) -> int:
        """Number of consecutive hours of the cheapest block (0 = off)."""
        return int(self.options.get(CONF_BLOCK_HOURS) or 0)

    async def _source(self) -> str | None:
        if chosen := self.options.get(CONF_FORECAST_IMPORT_ENTITY):
            return chosen
        if not self.options.get(CONF_FORECAST_AUTO, True):
            return None
        setup = await async_energy_setup(self.hass, self.options)
        return setup.import_price if setup else None

    async def _points(self, entity_id: str) -> Points:
        points = attribute_points(
            self.hass.states.get(entity_id),
            self.options.get(CONF_FORECAST_ATTRIBUTE) or None,
            self.options.get(CONF_FORECAST_VALUE_KEY) or None,
        )
        if points:
            return points
        result = await async_get_forecast(self.hass, entity_id)
        out: Points = []
        for ts, value in result.get("points") or []:
            if (parsed := _timestamp(ts)) is not None and _is_number(value):
                out.append((parsed, float(value)))
        return out

    async def _price_sensor(self) -> str | None:
        """The import price sensor (the recorded prices are those of this sensor)."""
        setup = await async_energy_setup(self.hass, self.options)
        return setup.import_price if setup else None

    async def _recorded(self, entity_id: str) -> Points:
        """Hourly prices of today so far, from the recorder statistics."""
        if "recorder" not in self.hass.config.components:
            return []
        try:
            stats = await get_instance(self.hass).async_add_executor_job(
                statistics_during_period,
                self.hass,
                dt_util.as_utc(dt_util.start_of_local_day()),
                None,
                {entity_id},
                "hour",
                None,
                {"mean"},
            )
        except Exception as err:  # noqa: BLE001 - best effort
            _LOGGER.debug("Could not read recorded prices of %s: %s", entity_id, err)
            return []
        return [
            (dt_util.utc_from_timestamp(row["start"]), float(row["mean"]))
            for row in stats.get(entity_id, [])
            if _is_number(row.get("mean")) and _is_number(row.get("start"))
        ]

    async def _async_update_data(self) -> HoursData:
        data = HoursData(
            cheapest_count=self.cheapest_count,
            expensive_count=self.expensive_count,
            block_count=self.block_count,
        )
        if not (data.cheapest_count or data.expensive_count or data.block_count):
            self._track(None)
            self.update_interval = UPDATE_INTERVAL
            return data
        data.source = await self._source()
        self._track(data.source)
        if not data.source:
            data.reason = "no_source"
        else:
            points = await self._points(data.source)
            if not points:
                data.reason = "no_prices"
            price_entity = await self._price_sensor()
            reference = None
            if price_entity and (state := self.hass.states.get(price_entity)):
                with contextlib.suppress(ValueError):
                    reference = float(state.state)
            factor = forecast_scale(points, reference)
            prices = hourly([(ts, value * factor) for ts, value in points])
            # Many integrations only list the upcoming prices: the hours that
            # have passed are taken from the recorded prices, so today still
            # has (almost) all of its hours.
            if price_entity:
                for hour, price in hourly(await self._recorded(price_entity)).items():
                    prices.setdefault(hour, price)
            # Only today and later: yesterday is of no use for "now" and "next".
            today = dt_util.start_of_local_day()
            prices = {h: p for h, p in prices.items() if h >= today}
            data.cheapest, data.expensive = calculate(
                prices, data.cheapest_count, data.expensive_count
            )
            if block := cheapest_block(prices, data.block_count, dt_util.now()):
                data.block_start, data.block_average = block
        found = bool(data.cheapest or data.expensive or data.block_start)
        if found:
            data.reason = None
        self.update_interval = UPDATE_INTERVAL if found else RETRY_INTERVAL
        return data
