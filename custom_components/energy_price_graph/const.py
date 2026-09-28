"""Constants for Energy Price Graph."""

from __future__ import annotations

DOMAIN = "energy_price_graph"

# URL under which the frontend module is served.
URL_BASE = "/energy_price_graph"
JS_FILE = "energy-price-graph.js"

ISSUE_TRACKER = "https://github.com/Gtolsma/HA-Energy-Price-Graph/issues"

CONF_PERIOD = "period"
CONF_VIEWS = "views"
CONF_TITLE = "title"
CONF_SHOW_EXPORT = "show_export"
CONF_MINMAX = "minmax"
CONF_LINE_STYLE = "line_style"
CONF_SHOW_NOW_LINE = "show_now_line"
CONF_SHOW_AVERAGE_LINE = "show_average_line"
CONF_CHEAPEST_HOURS = "cheapest_hours"
CONF_HIGHLIGHT_NEGATIVE = "highlight_negative"
CONF_SHOW_CURRENT = "show_current"
CONF_SHOW_PRICE_COLORS = "show_price_colors"
CONF_PRICE_COLOR_THRESHOLD = "price_color_threshold"
CONF_SHOW_AVERAGE = "show_average"
CONF_SHOW_SAVINGS = "show_savings"
CONF_SHOW_TIMING = "show_timing"
CONF_IMPORT_SURCHARGE = "import_surcharge"
CONF_EXPORT_SURCHARGE = "export_surcharge"
CONF_SHOW_GAS = "show_gas"
CONF_GAS_VIEWS = "gas_views"
CONF_IMPORT_ENTITY = "import_entity"
CONF_EXPORT_ENTITY = "export_entity"
CONF_GAS_ENTITY = "gas_entity"
CONF_IMPORT_NAME = "import_name"
CONF_EXPORT_NAME = "export_name"
CONF_FORECAST_AUTO = "forecast_auto"
CONF_FORECAST_IMPORT_ENTITY = "forecast_import_entity"
CONF_FORECAST_EXPORT_ENTITY = "forecast_export_entity"
CONF_FORECAST_GAS_ENTITY = "forecast_gas_entity"
CONF_FORECAST_ATTRIBUTE = "forecast_attribute"
CONF_FORECAST_VALUE_KEY = "forecast_value_key"

# Form sections (the stored options stay flat).
SECTION_GRAPH = "graph"
SECTION_MARKERS = "markers"
SECTION_CURRENT = "current"
SECTION_AVERAGE = "average"
SECTION_GAS = "gas"
SECTION_FORECAST = "forecast"
SECTION_ADVANCED = "advanced"
SECTIONS: dict[str, list[str]] = {
    SECTION_GRAPH: [
        CONF_PERIOD,
        CONF_LINE_STYLE,
        CONF_VIEWS,
        CONF_SHOW_EXPORT,
        CONF_MINMAX,
    ],
    SECTION_MARKERS: [
        CONF_SHOW_NOW_LINE,
        CONF_SHOW_AVERAGE_LINE,
        CONF_CHEAPEST_HOURS,
        CONF_HIGHLIGHT_NEGATIVE,
    ],
    SECTION_CURRENT: [
        CONF_SHOW_CURRENT,
        CONF_SHOW_PRICE_COLORS,
        CONF_PRICE_COLOR_THRESHOLD,
    ],
    SECTION_AVERAGE: [
        CONF_SHOW_AVERAGE,
        CONF_SHOW_SAVINGS,
        CONF_SHOW_TIMING,
        CONF_IMPORT_SURCHARGE,
        CONF_EXPORT_SURCHARGE,
    ],
    SECTION_GAS: [CONF_SHOW_GAS, CONF_GAS_VIEWS],
    SECTION_FORECAST: [
        CONF_FORECAST_AUTO,
        CONF_FORECAST_IMPORT_ENTITY,
        CONF_FORECAST_EXPORT_ENTITY,
        CONF_FORECAST_GAS_ENTITY,
        CONF_FORECAST_ATTRIBUTE,
        CONF_FORECAST_VALUE_KEY,
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
GAS_VIEWS = ["gas", "overview"]
LINE_STYLES = ["straight", "stepped", "smooth"]

DEFAULT_OPTIONS: dict = {
    CONF_PERIOD: "auto_fine",
    CONF_VIEWS: ["electricity", "overview"],
    CONF_SHOW_EXPORT: True,
    CONF_MINMAX: False,
    CONF_LINE_STYLE: "straight",
    CONF_SHOW_NOW_LINE: True,
    CONF_SHOW_AVERAGE_LINE: False,
    CONF_CHEAPEST_HOURS: 0,
    CONF_HIGHLIGHT_NEGATIVE: True,
    CONF_SHOW_CURRENT: True,
    CONF_SHOW_PRICE_COLORS: True,
    CONF_PRICE_COLOR_THRESHOLD: 10,
    CONF_SHOW_AVERAGE: True,
    CONF_SHOW_SAVINGS: True,
    CONF_SHOW_TIMING: True,
    CONF_IMPORT_SURCHARGE: 0,
    CONF_EXPORT_SURCHARGE: 0,
    CONF_SHOW_GAS: True,
    CONF_GAS_VIEWS: ["gas"],
    CONF_FORECAST_AUTO: True,
}

# Repair issues.
ISSUE_FRONTEND = "frontend_not_active"
ISSUE_NO_PRICE_SENSOR = "no_price_sensor"
