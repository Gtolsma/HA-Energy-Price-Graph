"""Config flow for Energy Price Graph."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
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
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
)

from .const import (
    CONF_EXPORT_ENTITY,
    CONF_EXPORT_NAME,
    CONF_FORECAST_EXPORT_ENTITY,
    CONF_FORECAST_GAS_ENTITY,
    CONF_FORECAST_IMPORT_ENTITY,
    CONF_GAS_ENTITY,
    CONF_IMPORT_ENTITY,
    CONF_IMPORT_NAME,
    CONF_LINE_STYLE,
    CONF_MINMAX,
    CONF_PERIOD,
    CONF_SHOW_AVERAGE,
    CONF_SHOW_CURRENT,
    CONF_SHOW_EXPORT,
    CONF_SHOW_GAS,
    CONF_SHOW_PRICE_COLORS,
    CONF_SHOW_SAVINGS,
    CONF_TITLE,
    CONF_VIEWS,
    DEFAULT_OPTIONS,
    DOMAIN,
    LINE_STYLES,
    PERIODS,
    SECTION_ADVANCED,
    SECTION_FORECAST,
    SECTIONS,
    VIEWS,
)

SENSOR = EntitySelector(EntitySelectorConfig(domain="sensor"))

OPTIONS_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_PERIOD): SelectSelector(
            SelectSelectorConfig(
                options=PERIODS,
                translation_key=CONF_PERIOD,
                mode=SelectSelectorMode.DROPDOWN,
            )
        ),
        vol.Required(CONF_LINE_STYLE): SelectSelector(
            SelectSelectorConfig(
                options=LINE_STYLES,
                translation_key=CONF_LINE_STYLE,
                mode=SelectSelectorMode.DROPDOWN,
            )
        ),
        vol.Required(CONF_VIEWS): SelectSelector(
            SelectSelectorConfig(
                options=VIEWS,
                translation_key=CONF_VIEWS,
                multiple=True,
                mode=SelectSelectorMode.LIST,
            )
        ),
        vol.Required(CONF_SHOW_EXPORT): BooleanSelector(),
        vol.Required(CONF_SHOW_CURRENT): BooleanSelector(),
        vol.Required(CONF_SHOW_PRICE_COLORS): BooleanSelector(),
        vol.Required(CONF_SHOW_AVERAGE): BooleanSelector(),
        vol.Required(CONF_SHOW_SAVINGS): BooleanSelector(),
        vol.Required(CONF_SHOW_GAS): BooleanSelector(),
        vol.Required(CONF_MINMAX): BooleanSelector(),
        vol.Required(SECTION_FORECAST): section(
            vol.Schema(
                {
                    vol.Optional(CONF_FORECAST_IMPORT_ENTITY): SENSOR,
                    vol.Optional(CONF_FORECAST_EXPORT_ENTITY): SENSOR,
                    vol.Optional(CONF_FORECAST_GAS_ENTITY): SENSOR,
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
    """Options: resolution, tabs, export line, overrides."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        errors: dict[str, str] = {}
        if user_input is not None:
            flat = flatten(user_input)
            if not flat.get(CONF_VIEWS):
                errors[CONF_VIEWS] = "no_views"
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
