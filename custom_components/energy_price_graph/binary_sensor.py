"""Binary sensors: is the current hour one of the cheapest / most expensive?"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .entity import device_info
from .hours import HoursCoordinator, periods

if TYPE_CHECKING:
    from . import EnergyPriceGraphConfigEntry

KINDS = ["cheapest", "expensive"]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EnergyPriceGraphConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the binary sensors."""
    coordinator = entry.runtime_data.hours
    async_add_entities(HourBinarySensor(coordinator, entry, kind) for kind in KINDS)


class HourBinarySensor(CoordinatorEntity[HoursCoordinator], BinarySensorEntity):
    """On during the cheapest (or most expensive) hours of the day."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: HoursCoordinator,
        entry: EnergyPriceGraphConfigEntry,
        kind: str,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        self._kind = kind
        self._attr_translation_key = f"{kind}_hours"
        self._attr_unique_id = f"{entry.entry_id}_{kind}_hours"
        self._attr_device_info = device_info(entry)

    @property
    def available(self) -> bool:
        """Unavailable when switched off in the options or without prices."""
        data = self.coordinator.data
        return super().available and data is not None and bool(data.hours(self._kind))

    @property
    def is_on(self) -> bool | None:
        """Whether the current hour is one of them."""
        data = self.coordinator.data
        return data.is_on(self._kind) if data else None

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """The hours of today and (when known) tomorrow."""
        data = self.coordinator.data
        if not data:
            return None
        hours = data.hours(self._kind)
        today = dt_util.start_of_local_day().date()
        return {
            "hours_per_day": data.cheapest_count
            if self._kind == "cheapest"
            else data.expensive_count,
            "today": [h.isoformat() for h in hours if h.date() == today],
            "tomorrow": [h.isoformat() for h in hours if h.date() > today],
            "periods": [
                {"start": s.isoformat(), "end": e.isoformat()}
                for s, e in periods(hours)
            ],
        }
