"""Tests for the setup and options forms."""

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
import pytest
import voluptuous as vol

from custom_components.energy_price_graph.config_flow import (
    OPTIONS_SCHEMA,
    flatten,
    nest,
)
from custom_components.energy_price_graph.const import (
    DEFAULT_OPTIONS,
    DOMAIN,
    SECTIONS,
)


async def _entry(hass: HomeAssistant) -> config_entries.ConfigEntry:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    await hass.async_block_till_done()
    return result["result"]


def _form(**options) -> dict:
    return nest({**DEFAULT_OPTIONS, **options})


def _suggested(result) -> dict:
    """Suggested (pre-filled) values of an options form, flattened."""
    out = {}
    for key in result["data_schema"].schema:
        if str(key) in SECTIONS:
            for inner in result["data_schema"].schema[key].schema.schema:
                suggested = (inner.description or {}).get("suggested_value")
                if suggested is not None:
                    out[str(inner)] = suggested
    return out


async def test_setup_form_has_no_fields(hass: HomeAssistant) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["data_schema"] is None

    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Energy Price Graph"
    assert result["data"] == {}
    # All defaults are stored, so the frontend gets a complete set.
    assert result["result"].options == DEFAULT_OPTIONS


async def test_options_form_is_prefilled_with_the_defaults(
    hass: HomeAssistant,
) -> None:
    entry = await _entry(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"
    # Every section of the form is there, in the order of SECTIONS.
    assert [str(k) for k in result["data_schema"].schema] == list(SECTIONS)
    assert _suggested(result) == DEFAULT_OPTIONS


async def test_options_form_shows_the_saved_options(hass: HomeAssistant) -> None:
    entry = await _entry(hass)
    hass.config_entries.async_update_entry(
        entry,
        options={**DEFAULT_OPTIONS, "cheapest_hours": 4, "title": "Stroom"},
    )
    result = await hass.config_entries.options.async_init(entry.entry_id)
    suggested = _suggested(result)
    assert suggested["cheapest_hours"] == 4
    assert suggested["title"] == "Stroom"


async def test_invalid_input_keeps_what_was_entered(hass: HomeAssistant) -> None:
    entry = await _entry(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], _form(views=[], cheapest_hours=5, expensive_hours=3)
    )
    assert result["errors"] == {"base": "no_views"}
    # The form is shown again with the values just entered, not the saved ones.
    suggested = _suggested(result)
    assert suggested["cheapest_hours"] == 5
    assert suggested["expensive_hours"] == 3
    # Nothing was saved.
    assert entry.options == DEFAULT_OPTIONS


async def test_gas_on_no_tab_is_fine_when_gas_is_off(hass: HomeAssistant) -> None:
    entry = await _entry(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], _form(show_gas=False, gas_views=[])
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options["show_gas"] is False


async def test_sliders_are_stored_as_whole_numbers(hass: HomeAssistant) -> None:
    entry = await _entry(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        _form(cheapest_hours=3.0, expensive_hours=2.0, price_color_threshold=15.0),
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    for key, value in (
        ("cheapest_hours", 3),
        ("expensive_hours", 2),
        ("price_color_threshold", 15),
    ):
        assert entry.options[key] == value
        assert isinstance(entry.options[key], int)


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("cheapest_hours", 13),
        ("expensive_hours", -1),
        ("price_color_threshold", 0),
        ("period", "week"),
        ("line_style", "dotted"),
        ("views", ["energy"]),
    ],
)
def test_schema_rejects_out_of_range_values(key: str, value) -> None:
    with pytest.raises(vol.Invalid):
        OPTIONS_SCHEMA(_form(**{key: value}))


def test_schema_accepts_the_defaults() -> None:
    assert flatten(OPTIONS_SCHEMA(_form())) == DEFAULT_OPTIONS


def test_every_option_is_in_exactly_one_section() -> None:
    keys = [k for section in SECTIONS.values() for k in section]
    assert len(keys) == len(set(keys))
    assert set(DEFAULT_OPTIONS) <= set(keys)
    # Every field in the form belongs to its section in SECTIONS.
    for name, section in OPTIONS_SCHEMA.schema.items():
        fields = {str(k) for k in section.schema.schema}
        assert fields == set(SECTIONS[str(name)])


def test_nest_and_flatten_round_trip() -> None:
    options = {**DEFAULT_OPTIONS, "title": "Prijs", "import_entity": "sensor.p"}
    assert flatten(nest(options)) == options
