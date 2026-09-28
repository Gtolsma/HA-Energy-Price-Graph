"""Energy Price Graph.

Adds a dynamic electricity price graph to the built-in Home Assistant Energy
dashboard by registering a small frontend module.
"""

from __future__ import annotations

import contextlib
from dataclasses import dataclass
import logging
from pathlib import Path
import time
from typing import Any

from aiohttp import web
from homeassistant.components import websocket_api
from homeassistant.components.energy.data import async_get_manager
from homeassistant.components.frontend import add_extra_js_url, remove_extra_js_url
from homeassistant.components.http import HomeAssistantView, StaticPathConfig
from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.const import Platform, __version__ as HA_VERSION
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import config_validation as cv, issue_registry as ir
from homeassistant.helpers.typing import ConfigType
from homeassistant.loader import async_get_integration
import voluptuous as vol

from .const import (
    DEFAULT_OPTIONS,
    DOMAIN,
    ISSUE_FRONTEND,
    ISSUE_NO_PRICE_SENSOR,
    ISSUE_TRACKER,
    JS_FILE,
    URL_BASE,
)
from .forecast import async_get_forecast
from .prefs import async_energy_setup

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.SENSOR]


@dataclass
class RuntimeData:
    """Data of a loaded entry."""

    loader_url: str


type EnergyPriceGraphConfigEntry = ConfigEntry[RuntimeData]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

_STATIC_REGISTERED = f"{DOMAIN}_static_registered"
_VERSION = f"{DOMAIN}_version"
_REPORTS = f"{DOMAIN}_reports"
_ENERGY_LISTENER = f"{DOMAIN}_energy_listener"
WS_TYPE_OPTIONS = f"{DOMAIN}/options"
WS_TYPE_REPORT = f"{DOMAIN}/report"
WS_TYPE_FORECAST = f"{DOMAIN}/forecast"

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


@websocket_api.websocket_command(
    {
        vol.Required("type"): WS_TYPE_REPORT,
        vol.Required("status"): vol.In(["ok", "failed", "not_active"]),
        vol.Optional("view"): str,
        vol.Optional("error"): vol.All(str, vol.Length(max=500)),
        vol.Optional("version"): str,
    }
)
@callback
def ws_report(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict
) -> None:
    """Receive whether the frontend module could extend the Energy dashboard.

    The module relies on internal frontend code; when a Home Assistant update
    breaks it, a repair issue tells the user instead of only a console line.
    """
    status = msg["status"]
    hass.data.setdefault(_REPORTS, {})[status] = {
        "time": time.time(),
        "view": msg.get("view"),
        "error": msg.get("error"),
        "module_version": msg.get("version"),
    }
    if status == "ok":
        ir.async_delete_issue(hass, DOMAIN, ISSUE_FRONTEND)
    elif current_options(hass) is not None:
        ir.async_create_issue(
            hass,
            DOMAIN,
            ISSUE_FRONTEND,
            is_fixable=False,
            severity=ir.IssueSeverity.WARNING,
            translation_key=ISSUE_FRONTEND,
            translation_placeholders={
                "ha_version": HA_VERSION,
                "error": msg.get("error") or "-",
                "issue_tracker": ISSUE_TRACKER,
            },
            learn_more_url=ISSUE_TRACKER,
        )
    connection.send_result(msg["id"])


@websocket_api.websocket_command(
    {vol.Required("type"): WS_TYPE_FORECAST, vol.Required("entity_id"): cv.entity_id}
)
@websocket_api.async_response
async def ws_forecast(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict
) -> None:
    """Send the upcoming prices of a price sensor, from its integration."""
    connection.send_result(msg["id"], await async_get_forecast(hass, msg["entity_id"]))


def frontend_reports(hass: HomeAssistant) -> dict[str, Any]:
    """Last report per status from the frontend module (for diagnostics)."""
    return dict(hass.data.get(_REPORTS) or {})


async def async_check_price_sensor(
    hass: HomeAssistant, options: dict[str, Any] | None = None
) -> None:
    """Raise a repair issue when there is no price sensor to show."""
    if options is None:
        options = current_options(hass)
    setup = await async_energy_setup(hass, options) if options is not None else None
    if (
        setup is not None
        and setup.has_grid
        and not setup.import_price
        and not setup.export_price
    ):
        ir.async_create_issue(
            hass,
            DOMAIN,
            ISSUE_NO_PRICE_SENSOR,
            is_fixable=False,
            severity=ir.IssueSeverity.WARNING,
            translation_key=ISSUE_NO_PRICE_SENSOR,
        )
    else:
        ir.async_delete_issue(hass, DOMAIN, ISSUE_NO_PRICE_SENSOR)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Register the websocket commands and the loader."""
    integration = await async_get_integration(hass, DOMAIN)
    hass.data[_VERSION] = str(integration.version)
    websocket_api.async_register_command(hass, ws_options)
    websocket_api.async_register_command(hass, ws_report)
    websocket_api.async_register_command(hass, ws_forecast)
    hass.http.register_view(LoaderView(hass))
    return True


async def _async_listen_energy(hass: HomeAssistant) -> None:
    """Re-check the price sensor when the energy settings change.

    The energy manager has no way to remove a listener, so it is added once
    and checks for a loaded entry itself.
    """
    if hass.data.get(_ENERGY_LISTENER):
        return
    try:
        manager = await async_get_manager(hass)
    except Exception:  # noqa: BLE001 - the energy integration is optional
        return

    async def _updated() -> None:
        await async_check_price_sensor(hass)

    manager.async_listen_updates(_updated)
    hass.data[_ENERGY_LISTENER] = True


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
    entry.runtime_data = RuntimeData(loader_url=LOADER_URL)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    await _async_listen_energy(hass)
    await async_check_price_sensor(hass, {**DEFAULT_OPTIONS, **entry.options})
    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: EnergyPriceGraphConfigEntry
) -> bool:
    """Unload a config entry."""
    if not await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        return False
    with contextlib.suppress(KeyError):
        remove_extra_js_url(hass, entry.runtime_data.loader_url)
    return True


async def async_remove_entry(
    hass: HomeAssistant, entry: EnergyPriceGraphConfigEntry
) -> None:
    """Remove the repair issues when the integration is removed."""
    ir.async_delete_issue(hass, DOMAIN, ISSUE_FRONTEND)
    ir.async_delete_issue(hass, DOMAIN, ISSUE_NO_PRICE_SENSOR)
