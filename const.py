"""Constants for Energy Price Graph."""

from __future__ import annotations

DOMAIN = "energy_price_graph"

# URL under which the frontend module is served.
URL_BASE = "/energy_price_graph"
JS_FILE = "energy-price-graph.js"

CONF_PERIOD = "period"
CONF_VIEWS = "views"
CONF_TITLE = "title"
CONF_SHOW_EXPORT = "show_export"
CONF_MINMAX = "minmax"
CONF_LINE_STYLE = "line_style"
CONF_SHOW_CURRENT = "show_current"
CONF_SHOW_PRICE_COLORS = "show_price_colors"
CONF_SHOW_AVERAGE = "show_average"
CONF_SHOW_SAVINGS = "show_savings"
CONF_SHOW_GAS = "show_gas"
CONF_IMPORT_ENTITY = "import_entity"
CONF_EXPORT_ENTITY = "export_entity"
CONF_GAS_ENTITY = "gas_entity"
CONF_IMPORT_NAME = "import_name"
CONF_EXPORT_NAME = "export_name"
CONF_FORECAST_IMPORT_ENTITY = "forecast_import_entity"
CONF_FORECAST_EXPORT_ENTITY = "forecast_export_entity"
CONF_FORECAST_GAS_ENTITY = "forecast_gas_entity"

# Form sections (the stored options stay flat).
SECTION_FORECAST = "forecast"
SECTION_ADVANCED = "advanced"
SECTIONS: dict[str, list[str]] = {
    SECTION_FORECAST: [
        CONF_FORECAST_IMPORT_ENTITY,
        CONF_FORECAST_EXPORT_ENTITY,
        CONF_FORECAST_GAS_ENTITY,
    ],
    SECTION_ADVANCED: [
        CONF_TITLE,
        CONF_IMPORT_ENTITY,
        CONF_EXPORT_ENTITY,
        CONF_GAS_ENTITY,
        CONF_IMPORT_NAME,
        CONF_EXPORT_NAME,
    ],
}

PERIODS = ["auto_fine", "auto", "5minute", "hour", "day"]
VIEWS = ["electricity", "overview"]
LINE_STYLES = ["straight", "stepped", "smooth"]

DEFAULT_OPTIONS: dict = {
    CONF_PERIOD: "auto_fine",
    CONF_VIEWS: ["electricity", "overview"],
    CONF_SHOW_EXPORT: True,
    CONF_MINMAX: False,
    CONF_LINE_STYLE: "straight",
    CONF_SHOW_CURRENT: True,
    CONF_SHOW_PRICE_COLORS: True,
    CONF_SHOW_AVERAGE: True,
    CONF_SHOW_SAVINGS: True,
    CONF_SHOW_GAS: True,
}
