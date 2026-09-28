"""Sensors with your average prices and the result compared with the market."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta
import logging
from typing import TYPE_CHECKING, Any

from homeassistant.components.recorder import get_instance
from homeassistant.components.recorder.statistics import statistics_during_period
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)
from homeassistant.util import dt as dt_util

from .calc import Paid, market_price, mean, paid_average, result
from .const import CONF_EXPORT_SURCHARGE, CONF_IMPORT_SURCHARGE, DEFAULT_OPTIONS, DOMAIN
from .prefs import EnergySetup, async_energy_setup

if TYPE_CHECKING:
    from . import EnergyPriceGraphConfigEntry

_LOGGER = logging.getLogger(__name__)

UPDATE_INTERVAL = timedelta(minutes=15)

KEYS = ["import_paid", "import_market", "export_paid", "export_market", "result"]


def _start_of_today() -> datetime:
    return dt_util.start_of_local_day()


def _start_of_month() -> datetime:
    return dt_util.start_of_local_day().replace(day=1)


PERIODS: dict[str, Callable[[], datetime]] = {
    "today": _start_of_today,
    "month": _start_of_month,
}

type PeriodValues = dict[str, float | None]


class PriceStatsCoordinator(DataUpdateCoordinator[dict[str, PeriodValues]]):
    """Calculate the averages from the recorder statistics."""

    def __init__(self, hass: HomeAssistant, entry: EnergyPriceGraphConfigEntry) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=UPDATE_INTERVAL,
        )
        self.options = {**DEFAULT_OPTIONS, **entry.options}

    async def _async_update_data(self) -> dict[str, PeriodValues]:
        """Fetch the statistics and calculate the values per period."""
        if "recorder" not in self.hass.config.components:
            return {}
        setup = await async_energy_setup(self.hass, self.options)
        if setup is None or not setup.has_grid:
            return {}
        return {
            period: await self._period(setup, start())
            for period, start in PERIODS.items()
        }

    async def _stats(
        self, start: datetime, ids: set[str], types: set[Any]
    ) -> dict[str, list[Any]]:
        if not ids:
            return {}
        return await get_instance(self.hass).async_add_executor_job(
            statistics_during_period,
            self.hass,
            dt_util.as_utc(start),
            None,
            ids,
            "hour",
            {"energy": "kWh"},
            types,
        )

    async def _period(self, setup: EnergySetup, start: datetime) -> PeriodValues:
        flows = [f for f in setup.imports + setup.exports if f.cost]
        ids = {f.energy for f in flows} | {f.cost for f in flows if f.cost}
        changes = await self._stats(start, ids, {"change"})
        price_ids = {p for p in (setup.import_price, setup.export_price) if p}
        prices = await self._stats(start, price_ids, {"mean"})

        def paid(flows_: list[Any]) -> Paid | None:
            return paid_average(
                (changes.get(f.energy), changes.get(f.cost)) for f in flows_ if f.cost
            )

        def market(
            entity: str | None, fixed: float | None, surcharge: Any
        ) -> float | None:
            avg = mean(prices.get(entity)) if entity else None
            return market_price(avg, fixed, float(surcharge or 0))

        imp = paid(setup.imports)
        imp_market = market(
            setup.import_price,
            setup.import_fixed,
            self.options.get(CONF_IMPORT_SURCHARGE),
        )
        values: PeriodValues = {
            "import_paid": imp.avg if imp else None,
            "import_market": imp_market,
        }
        exp = exp_market = None
        if setup.exports or setup.export_price:
            exp = paid(setup.exports)
            exp_market = market(
                setup.export_price,
                setup.export_fixed,
                self.options.get(CONF_EXPORT_SURCHARGE),
            )
            values["export_paid"] = exp.avg if exp else None
            values["export_market"] = exp_market
        values["result"] = result(imp, imp_market, exp, exp_market)
        return values


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EnergyPriceGraphConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the sensors."""
    coordinator = PriceStatsCoordinator(hass, entry)
    await coordinator.async_refresh()
    async_add_entities(
        PriceStatSensor(coordinator, entry, key, period)
        for period in PERIODS
        for key in KEYS
    )


class PriceStatSensor(CoordinatorEntity[PriceStatsCoordinator], SensorEntity):
    """An average price or the result compared with the market."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: PriceStatsCoordinator,
        entry: EnergyPriceGraphConfigEntry,
        key: str,
        period: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._key = key
        self._period = period
        self._attr_translation_key = f"{key}_{period}"
        self._attr_unique_id = f"{entry.entry_id}_{key}_{period}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Energy Price Graph",
            entry_type=DeviceEntryType.SERVICE,
        )
        currency = coordinator.hass.config.currency
        if key == "result":
            self._attr_device_class = SensorDeviceClass.MONETARY
            self._attr_state_class = SensorStateClass.TOTAL
            self._attr_native_unit_of_measurement = currency
            self._attr_suggested_display_precision = 2
        else:
            self._attr_state_class = SensorStateClass.MEASUREMENT
            self._attr_native_unit_of_measurement = f"{currency}/kWh"
            self._attr_suggested_display_precision = 3

    @property
    def available(self) -> bool:
        """Unavailable without data, e.g. export sensors without export."""
        values = (self.coordinator.data or {}).get(self._period)
        return super().available and values is not None and self._key in values

    @property
    def native_value(self) -> float | None:
        """Return the value."""
        value = ((self.coordinator.data or {}).get(self._period) or {}).get(self._key)
        return round(value, 5) if value is not None else None

    @property
    def last_reset(self) -> datetime | None:
        """Start of the period, for the result sensor."""
        if self._key != "result":
            return None
        return PERIODS[self._period]()
