"""Config flow for Energy Price Graph."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlowWithReload,
)
from homeassistant.core import callback
from homeassistant.data_entry_flow import section
from homeassistant.helpers.selector import (
    BooleanSelector,
    EntitySelector,
    EntitySelectorConfig,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
)
import voluptuous as vol

from .const import (
    CONF_CHEAPEST_HOURS,
    CONF_EXPORT_ENTITY,
    CONF_EXPORT_NAME,
    CONF_EXPORT_SURCHARGE,
    CONF_FORECAST_ATTRIBUTE,
    CONF_FORECAST_AUTO,
    CONF_FORECAST_EXPORT_ENTITY,
    CONF_FORECAST_GAS_ENTITY,
    CONF_FORECAST_IMPORT_ENTITY,
    CONF_FORECAST_VALUE_KEY,
    CONF_GAS_ENTITY,
    CONF_GAS_VIEWS,
    CONF_HIGHLIGHT_NEGATIVE,
    CONF_IMPORT_ENTITY,
    CONF_IMPORT_NAME,
    CONF_IMPORT_SURCHARGE,
    CONF_LINE_STYLE,
    CONF_MINMAX,
    CONF_PERIOD,
    CONF_PRICE_COLOR_THRESHOLD,
    CONF_SHOW_AVERAGE,
    CONF_SHOW_AVERAGE_LINE,
    CONF_SHOW_CURRENT,
    CONF_SHOW_EXPORT,
    CONF_SHOW_GAS,
    CONF_SHOW_NOW_LINE,
    CONF_SHOW_PRICE_COLORS,
    CONF_SHOW_SAVINGS,
    CONF_SHOW_TIMING,
    CONF_TITLE,
    CONF_VIEWS,
    DEFAULT_OPTIONS,
    DOMAIN,
    GAS_VIEWS,
    LINE_STYLES,
    PERIODS,
    SECTION_ADVANCED,
    SECTION_AVERAGE,
    SECTION_CURRENT,
    SECTION_FORECAST,
    SECTION_GAS,
    SECTION_GRAPH,
    SECTION_MARKERS,
    SECTIONS,
    VIEWS,
)

SENSOR = EntitySelector(EntitySelectorConfig(domain="sensor"))
SURCHARGE = NumberSelector(
    NumberSelectorConfig(min=-10, max=10, step="any", mode=NumberSelectorMode.BOX)
)


def _select(options: list[str], key: str, *, multiple: bool = False) -> SelectSelector:
    return SelectSelector(
        SelectSelectorConfig(
            options=options,
            translation_key=key,
            multiple=multiple,
            mode=SelectSelectorMode.LIST if multiple else SelectSelectorMode.DROPDOWN,
        )
    )


OPTIONS_SCHEMA = vol.Schema(
    {
        vol.Required(SECTION_GRAPH): section(
            vol.Schema(
                {
                    vol.Required(CONF_PERIOD): _select(PERIODS, CONF_PERIOD),
                    vol.Required(CONF_LINE_STYLE): _select(
                        LINE_STYLES, CONF_LINE_STYLE
                    ),
                    vol.Required(CONF_VIEWS): _select(VIEWS, CONF_VIEWS, multiple=True),
                    vol.Required(CONF_SHOW_EXPORT): BooleanSelector(),
                    vol.Required(CONF_MINMAX): BooleanSelector(),
                }
            ),
            {"collapsed": False},
        ),
        vol.Required(SECTION_MARKERS): section(
            vol.Schema(
                {
                    vol.Required(CONF_SHOW_NOW_LINE): BooleanSelector(),
                    vol.Required(CONF_SHOW_AVERAGE_LINE): BooleanSelector(),
                    vol.Required(CONF_CHEAPEST_HOURS): vol.All(
                        NumberSelector(
                            NumberSelectorConfig(
                                min=0, max=12, step=1, mode=NumberSelectorMode.SLIDER
                            )
                        ),
                        vol.Coerce(int),
                    ),
                    vol.Required(CONF_HIGHLIGHT_NEGATIVE): BooleanSelector(),
                }
            ),
            {"collapsed": False},
        ),
        vol.Required(SECTION_CURRENT): section(
            vol.Schema(
                {
                    vol.Required(CONF_SHOW_CURRENT): BooleanSelector(),
                    vol.Required(CONF_SHOW_PRICE_COLORS): BooleanSelector(),
                    vol.Required(CONF_PRICE_COLOR_THRESHOLD): vol.All(
                        NumberSelector(
                            NumberSelectorConfig(
                                min=1,
                                max=50,
                                step=1,
                                unit_of_measurement="%",
                                mode=NumberSelectorMode.SLIDER,
                            )
                        ),
                        vol.Coerce(int),
                    ),
                }
            ),
            {"collapsed": False},
        ),
        vol.Required(SECTION_AVERAGE): section(
            vol.Schema(
                {
                    vol.Required(CONF_SHOW_AVERAGE): BooleanSelector(),
                    vol.Required(CONF_SHOW_SAVINGS): BooleanSelector(),
                    vol.Required(CONF_SHOW_TIMING): BooleanSelector(),
                    vol.Required(CONF_IMPORT_SURCHARGE): SURCHARGE,
                    vol.Required(CONF_EXPORT_SURCHARGE): SURCHARGE,
                }
            ),
            {"collapsed": False},
        ),
        vol.Required(SECTION_GAS): section(
            vol.Schema(
                {
                    vol.Required(CONF_SHOW_GAS): BooleanSelector(),
                    vol.Required(CONF_GAS_VIEWS): _select(
                        GAS_VIEWS, CONF_GAS_VIEWS, multiple=True
                    ),
                }
            ),
            {"collapsed": False},
        ),
        vol.Required(SECTION_FORECAST): section(
            vol.Schema(
                {
                    vol.Required(CONF_FORECAST_AUTO): BooleanSelector(),
                    vol.Optional(CONF_FORECAST_IMPORT_ENTITY): SENSOR,
                    vol.Optional(CONF_FORECAST_EXPORT_ENTITY): SENSOR,
                    vol.Optional(CONF_FORECAST_GAS_ENTITY): SENSOR,
                    vol.Optional(CONF_FORECAST_ATTRIBUTE): TextSelector(),
                    vol.Optional(CONF_FORECAST_VALUE_KEY): TextSelector(),
                }
            ),
            {"collapsed": True},
        ),
        vol.Required(SECTION_ADVANCED): section(
            vol.Schema(
                {
                    vol.Optional(CONF_TITLE): TextSelector(),
                    vol.Optional(CONF_IMPORT_ENTITY): SENSOR,
                    vol.Optional(CONF_EXPORT_ENTITY): SENSOR,
                    vol.Optional(CONF_GAS_ENTITY): SENSOR,
                    vol.Optional(CONF_IMPORT_NAME): TextSelector(),
                    vol.Optional(CONF_EXPORT_NAME): TextSelector(),
                }
            ),
            {"collapsed": True},
        ),
    }
)


def flatten(user_input: dict[str, Any]) -> dict[str, Any]:
    """Move the values of the form sections to the top level."""
    flat = {k: v for k, v in user_input.items() if k not in SECTIONS}
    for name in SECTIONS:
        flat.update(user_input.get(name) or {})
    return flat


def nest(options: dict[str, Any]) -> dict[str, Any]:
    """Group flat options into the form sections (for suggested values)."""
    nested = {
        k: v
        for k, v in options.items()
        if not any(k in keys for keys in SECTIONS.values())
    }
    for name, keys in SECTIONS.items():
        nested[name] = {k: options[k] for k in keys if k in options}
    return nested


class EnergyPriceGraphConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the initial setup (no questions, everything is in options)."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the user step."""
        if user_input is not None:
            return self.async_create_entry(
                title="Energy Price Graph", data={}, options=dict(DEFAULT_OPTIONS)
            )
        return self.async_show_form(step_id="user")

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: ConfigEntry,
    ) -> EnergyPriceGraphOptionsFlow:
        """Return the options flow."""
        return EnergyPriceGraphOptionsFlow()


class EnergyPriceGraphOptionsFlow(OptionsFlowWithReload):
    """Options: graph, markers, current price, average, gas, forecast."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        errors: dict[str, str] = {}
        if user_input is not None:
            flat = flatten(user_input)
            if not flat.get(CONF_VIEWS):
                errors["base"] = "no_views"
            elif flat.get(CONF_SHOW_GAS) and not flat.get(CONF_GAS_VIEWS):
                errors["base"] = "no_gas_views"
            else:
                return self.async_create_entry(data=flat)

        suggested = {**DEFAULT_OPTIONS, **self.config_entry.options}
        if user_input is not None:
            suggested.update(flatten(user_input))
        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(
                OPTIONS_SCHEMA, nest(suggested)
            ),
            errors=errors,
        )
