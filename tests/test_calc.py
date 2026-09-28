"""Tests for the average price calculation and reading the energy settings."""

from custom_components.energy_price_graph.calc import (
    Paid,
    market_price,
    mean,
    paid_average,
    result,
)
from custom_components.energy_price_graph.prefs import (
    Flow,
    apply_overrides,
    parse_prefs,
)


def _rows(key: str, values: list[float | None]) -> list[dict]:
    return [{"start": i, key: v} for i, v in enumerate(values)]


def test_paid_average_divides_cost_by_energy() -> None:
    paid = paid_average([(_rows("change", [1, 3]), _rows("change", [0.2, 0.6]))])
    assert paid is not None
    assert paid.energy == 4
    assert abs(paid.avg - 0.2) < 1e-9


def test_paid_average_keeps_negative_cost() -> None:
    # 1 kWh at +0.30 and 1 kWh at -0.10: 0.10 per kWh on average.
    paid = paid_average([(_rows("change", [1, 1]), _rows("change", [0.3, -0.1]))])
    assert paid is not None
    assert abs(paid.avg - 0.1) < 1e-9


def test_paid_average_skips_incomplete_periods() -> None:
    energy = _rows("change", [1, 2, 0])
    cost = [{"start": 0, "change": 0.25}, {"start": 2, "change": 5}]
    assert paid_average([(energy, cost)]) == Paid(0.25, 1)
    assert paid_average([(energy, None)]) is None
    assert paid_average([]) is None


def test_mean_and_market_price() -> None:
    assert mean(_rows("mean", [0.1, None, 0.3])) == 0.2
    assert mean([]) is None
    assert market_price(0.2, 0.3, 0.1) == 0.30000000000000004
    assert market_price(None, 0.3, 0.1) == 0.3
    assert market_price(None, None) is None


def test_result() -> None:
    value = result(Paid(0.2, 10), 0.25, Paid(0.05, 4), 0.1)
    assert value is not None
    assert abs(value - 0.3) < 1e-9
    assert result(None, 0.25, None, None) is None


def test_parse_prefs_older_schema() -> None:
    prefs = {
        "energy_sources": [
            {
                "type": "grid",
                "flow_from": [
                    {
                        "stat_energy_from": "sensor.in",
                        "stat_cost": None,
                        "entity_energy_price": "sensor.price",
                        "number_energy_price": None,
                    }
                ],
                "flow_to": [
                    {
                        "stat_energy_to": "sensor.out",
                        "stat_compensation": "sensor.comp",
                        "entity_energy_price": None,
                        "number_energy_price": 0.07,
                    }
                ],
            },
            {"type": "gas", "entity_energy_price": "sensor.gas_price"},
        ]
    }
    setup = parse_prefs(prefs, {"sensor.in": "sensor.in_cost"})
    assert setup.has_grid
    assert setup.import_price == "sensor.price"
    assert setup.export_price is None
    assert setup.export_fixed == 0.07
    assert setup.gas_price == "sensor.gas_price"
    assert setup.imports == [Flow("sensor.in", "sensor.in_cost")]
    assert setup.exports == [Flow("sensor.out", "sensor.comp")]


def test_parse_prefs_current_schema_and_overrides() -> None:
    prefs = {
        "energy_sources": [
            {
                "type": "grid",
                "stat_energy_from": "sensor.in",
                "stat_cost": "sensor.cost",
                "entity_energy_price": "sensor.price",
                "stat_energy_to": "sensor.out",
                "entity_energy_price_export": "sensor.export_price",
            }
        ]
    }
    setup = apply_overrides(parse_prefs(prefs), {"export_entity": "sensor.other"})
    assert setup.import_price == "sensor.price"
    assert setup.export_price == "sensor.other"
    assert setup.imports == [Flow("sensor.in", "sensor.cost")]
    assert setup.exports == [Flow("sensor.out", None)]


def test_parse_prefs_empty() -> None:
    setup = parse_prefs(None)
    assert not setup.has_grid
    assert setup.imports == []
