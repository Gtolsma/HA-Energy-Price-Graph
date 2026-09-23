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
    CONF_IMPORT_ENTITY,
    CONF_IMPORT_NAME,
    CONF_LINE_STYLE,
    CONF_MINMAX,
    CONF_PERIOD,
    CONF_SHOW_AVERAGE,
    CONF_SHOW_CURRENT,
    CONF_SHOW_EXPORT,
    CONF_TITLE,
    CONF_VIEWS,
    DEFAULT_OPTIONS,
    DOMAIN,
    LINE_STYLES,
    PERIODS,
    VIEWS,
)

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
        vol.Required(CONF_SHOW_AVERAGE): BooleanSelector(),
        vol.Required(CONF_MINMAX): BooleanSelector(),
        vol.Optional(CONF_TITLE): TextSelector(),
        vol.Optional(CONF_IMPORT_ENTITY): EntitySelector(
            EntitySelectorConfig(domain="sensor")
        ),
        vol.Optional(CONF_EXPORT_ENTITY): EntitySelector(
            EntitySelectorConfig(domain="sensor")
        ),
        vol.Optional(CONF_IMPORT_NAME): TextSelector(),
        vol.Optional(CONF_EXPORT_NAME): TextSelector(),
    }
)


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
            if not user_input.get(CONF_VIEWS):
                errors[CONF_VIEWS] = "no_views"
            else:
                return self.async_create_entry(data=user_input)

        suggested = {**DEFAULT_OPTIONS, **self.config_entry.options}
        if user_input is not None:
            suggested.update(user_input)
        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(OPTIONS_SCHEMA, suggested),
            errors=errors,
        )
