"""Energy Price Graph.

Adds a dynamic electricity price graph to the built-in Home Assistant Energy
dashboard by registering a small frontend module.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.components.frontend import add_extra_js_url, remove_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType
from homeassistant.loader import async_get_integration

from .const import DEFAULT_OPTIONS, DOMAIN, JS_FILE, URL_BASE

type EnergyPriceGraphConfigEntry = ConfigEntry[str]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

_STATIC_REGISTERED = f"{DOMAIN}_static_registered"
WS_TYPE_OPTIONS = f"{DOMAIN}/options"


def build_module_url(version: str) -> str:
    """Build the module URL.

    Only the version is part of the URL, so the browser fetches a fresh copy
    after an update. The options are read by the script over the websocket
    API, so changing them needs no browser refresh.
    """
    return f"{URL_BASE}/{JS_FILE}?v={version}"


def current_options(hass: HomeAssistant) -> dict[str, Any] | None:
    """Return the effective options of the loaded entry, or None."""
    for entry in hass.config_entries.async_entries(DOMAIN):
        if entry.state is ConfigEntryState.LOADED:
            return {**DEFAULT_OPTIONS, **entry.options}
    return None


@websocket_api.websocket_command({vol.Required("type"): WS_TYPE_OPTIONS})
@callback
def ws_options(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict
) -> None:
    """Send the current options to the frontend module."""
    connection.send_result(msg["id"], {"options": current_options(hass)})


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Register the websocket command."""
    websocket_api.async_register_command(hass, ws_options)
    return True


async def async_setup_entry(
    hass: HomeAssistant, entry: EnergyPriceGraphConfigEntry
) -> bool:
    """Set up Energy Price Graph from a config entry."""
    # Static paths cannot be unregistered, so only register them once.
    if not hass.data.get(_STATIC_REGISTERED):
        await hass.http.async_register_static_paths(
            [StaticPathConfig(URL_BASE, str(Path(__file__).parent / "frontend"), False)]
        )
        hass.data[_STATIC_REGISTERED] = True

    integration = await async_get_integration(hass, DOMAIN)
    url = build_module_url(str(integration.version))
    add_extra_js_url(hass, url)
    entry.runtime_data = url
    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: EnergyPriceGraphConfigEntry
) -> bool:
    """Unload a config entry."""
    try:
        remove_extra_js_url(hass, entry.runtime_data)
    except KeyError:
        pass
    return True
