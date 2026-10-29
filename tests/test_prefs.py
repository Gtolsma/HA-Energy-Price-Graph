"""Tests for reading the energy preferences."""

from __future__ import annotations

import logging

import pytest

from custom_components.energy_price_graph import prefs
from custom_components.energy_price_graph.prefs import read_cost_sensors


@pytest.fixture(autouse=True)
def _reset_warnings():
    prefs._WARNED.clear()
    yield
    prefs._WARNED.clear()


def test_read_cost_sensors_normal() -> None:
    """The usual shape is used as is."""
    data = {"cost_sensors": {"sensor.in": "sensor.in_cost"}}
    assert read_cost_sensors(data) == {"sensor.in": "sensor.in_cost"}


def test_read_cost_sensors_missing() -> None:
    """No energy data or no cost sensors is not a problem."""
    assert read_cost_sensors(None) == {}
    assert read_cost_sensors({}) == {}


def test_read_cost_sensors_changed_shape(caplog: pytest.LogCaptureFixture) -> None:
    """A changed shape gives an empty mapping and one warning."""
    with caplog.at_level(logging.WARNING):
        assert read_cost_sensors({"cost_sensors": ["sensor.in"]}) == {}
        assert read_cost_sensors({"cost_sensors": ["sensor.in"]}) == {}
        assert read_cost_sensors("energy") == {}
    assert caplog.text.count("Unexpected format of the energy cost sensors") == 1
    assert "Unexpected energy integration data" in caplog.text


def test_read_cost_sensors_skips_odd_items(caplog: pytest.LogCaptureFixture) -> None:
    """Items that are not entity ids are skipped with a warning."""
    with caplog.at_level(logging.WARNING):
        out = read_cost_sensors(
            {"cost_sensors": {"sensor.a": "sensor.a_cost", "sensor.b": {"id": 1}}}
        )
    assert out == {"sensor.a": "sensor.a_cost"}
    assert "unexpected format and are skipped" in caplog.text
