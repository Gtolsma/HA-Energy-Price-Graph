"""Shared parts of the entities."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo

from .const import DOMAIN

if TYPE_CHECKING:
    from . import EnergyPriceGraphConfigEntry


def device_info(entry: EnergyPriceGraphConfigEntry) -> DeviceInfo:
    """The service device that holds all sensors."""
    return DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        name="Energy Price Graph",
        entry_type=DeviceEntryType.SERVICE,
    )
