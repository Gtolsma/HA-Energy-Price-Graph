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
CONF_IMPORT_ENTITY = "import_entity"
CONF_EXPORT_ENTITY = "export_entity"
CONF_IMPORT_NAME = "import_name"
CONF_EXPORT_NAME = "export_name"

PERIODS = ["auto", "5minute", "hour", "day"]
VIEWS = ["electricity", "overview"]
LINE_STYLES = ["stepped", "straight", "smooth"]

DEFAULT_OPTIONS: dict = {
    CONF_PERIOD: "auto",
    CONF_VIEWS: ["electricity", "overview"],
    CONF_SHOW_EXPORT: True,
    CONF_MINMAX: False,
    CONF_LINE_STYLE: "stepped",
}
