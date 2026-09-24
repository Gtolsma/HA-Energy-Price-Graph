"""Energy Price Graph.

Adds a dynamic electricity price graph to the built-in Home Assistant Energy
dashboard by registering a small frontend module.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import voluptuous as vol
from aiohttp import web
from homeassistant.components import websocket_api
from homeassistant.components.frontend import add_extra_js_url, remove_extra_js_url
from homeassistant.components.http import HomeAssistantView, StaticPathConfig
from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType
from homeassistant.loader import async_get_integration

from .const import DEFAULT_OPTIONS, DOMAIN, JS_FILE, URL_BASE

type EnergyPriceGraphConfigEntry = ConfigEntry[str]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

_STATIC_REGISTERED = f"{DOMAIN}_static_registered"
_VERSION = f"{DOMAIN}_version"
WS_TYPE_OPTIONS = f"{DOMAIN}/options"

# The frontend loads this small loader on every page load. Its URL never
# changes and it is never cached, so the browser always gets a loader that
# imports the module of the version that is installed right now, even when
# an old page (or a cached copy of it) still refers to the loader.
LOADER_URL = f"{URL_BASE}_loader.js"


def build_module_url(version: str) -> str:
    """Build the URL of the versioned frontend module."""
    return f"{URL_BASE}/{JS_FILE}?v={version}"


class LoaderView(HomeAssistantView):
    """Serve the loader that imports the current frontend module."""

    url = LOADER_URL
    name = f"{DOMAIN}:loader"
    requires_auth = False

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the view."""
        self.hass = hass

    async def get(self, request: web.Request) -> web.Response:
        """Return the loader script."""
        version = self.hass.data.get(_VERSION, "0")
        return web.Response(
            text=f'import "{build_module_url(version)}";\n',
            content_type="text/javascript",
            headers={"Cache-Control": "no-store"},
        )


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
    connection.send_result(
        msg["id"],
        {"options": current_options(hass), "version": hass.data.get(_VERSION)},
    )


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Register the websocket command and the loader."""
    integration = await async_get_integration(hass, DOMAIN)
    hass.data[_VERSION] = str(integration.version)
    websocket_api.async_register_command(hass, ws_options)
    hass.http.register_view(LoaderView(hass))
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

    add_extra_js_url(hass, LOADER_URL)
    entry.runtime_data = LOADER_URL
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
