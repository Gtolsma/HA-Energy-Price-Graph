"""Energy Price Graph.

Adds a dynamic electricity price graph to the built-in Home Assistant Energy
dashboard by registering a small frontend module.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from urllib.parse import urlencode

from homeassistant.components.frontend import add_extra_js_url, remove_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.loader import async_get_integration

from .const import (
    CONF_EXPORT_ENTITY,
    CONF_EXPORT_NAME,
    CONF_IMPORT_ENTITY,
    CONF_IMPORT_NAME,
    CONF_MINMAX,
    CONF_PERIOD,
    CONF_SHOW_EXPORT,
    CONF_TITLE,
    CONF_VIEWS,
    DEFAULT_OPTIONS,
    DOMAIN,
    JS_FILE,
    URL_BASE,
)

type EnergyPriceGraphConfigEntry = ConfigEntry[str]

_STATIC_REGISTERED = f"{DOMAIN}_static_registered"


def build_module_url(version: str, options: dict) -> str:
    """Build the module URL; options are passed to the script as query params."""
    opts = {**DEFAULT_OPTIONS, **options}
    params: dict[str, str] = {
        "period": opts[CONF_PERIOD],
        "views": ",".join(opts[CONF_VIEWS]),
        "export": "1" if opts[CONF_SHOW_EXPORT] else "0",
        "minmax": "1" if opts[CONF_MINMAX] else "0",
    }
    for key, param in (
        (CONF_TITLE, "title"),
        (CONF_IMPORT_ENTITY, "entity"),
        (CONF_EXPORT_ENTITY, "export_entity"),
        (CONF_IMPORT_NAME, "import_name"),
        (CONF_EXPORT_NAME, "export_name"),
    ):
        if value := opts.get(key):
            params[param] = value

    # Version + hash of the options so browsers fetch a fresh copy after
    # an update or an options change.
    digest = hashlib.sha1(json.dumps(params, sort_keys=True).encode()).hexdigest()[:8]
    params = {"v": f"{version}-{digest}", **params}
    return f"{URL_BASE}/{JS_FILE}?{urlencode(params)}"


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
    url = build_module_url(str(integration.version), dict(entry.options))
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
