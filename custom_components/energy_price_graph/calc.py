"""Average prices and the result compared with the market.

The same calculation as the average price card in the frontend:
- "paid": what you actually paid (import) or received (export) per kWh,
  cost ÷ energy, from the statistics the Energy dashboard uses;
- "market": the plain average of the price sensor over the period.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

Rows = Sequence[Mapping[str, Any]]


@dataclass
class Paid:
    """Money per kWh over a period and the energy it is based on."""

    avg: float
    energy: float


def paid_average(pairs: Iterable[tuple[Rows | None, Rows | None]]) -> Paid | None:
    """Money per kWh for (energy rows, cost rows) pairs.

    Only periods in which both statistics have a value and energy actually
    flowed are counted, so a sensor that was added halfway through does not
    skew the result. The sign of the cost is kept: with a negative price the
    cost (or compensation) of that period is negative.
    """
    energy = 0.0
    money = 0.0
    for energy_rows, cost_rows in pairs:
        if not energy_rows or not cost_rows:
            continue
        cost_by_start = {
            r.get("start"): r["change"]
            for r in cost_rows
            if isinstance(r.get("change"), (int, float))
        }
        for row in energy_rows:
            change = row.get("change")
            cost = cost_by_start.get(row.get("start"))
            if not isinstance(change, (int, float)) or change <= 0 or cost is None:
                continue
            energy += change
            money += cost
    return Paid(money / energy, energy) if energy > 0 else None


def mean(rows: Rows | None) -> float | None:
    """Plain average of the "mean" values of statistic rows."""
    values = [r["mean"] for r in rows or [] if isinstance(r.get("mean"), (int, float))]
    return sum(values) / len(values) if values else None


def market_price(
    average: float | None, fixed: float | None, surcharge: float = 0
) -> float | None:
    """Market price: sensor average plus surcharge, or else the fixed price."""
    if average is not None:
        return average + (surcharge or 0)
    return fixed


def result(
    import_paid: Paid | None,
    import_market: float | None,
    export_paid: Paid | None,
    export_market: float | None,
) -> float | None:
    """Result compared with the market average; positive is better.

    Import: (market - you) x kWh bought. Export: (you - market) x kWh sold.
    """
    parts = []
    if import_paid is not None and import_market is not None:
        parts.append((import_market - import_paid.avg) * import_paid.energy)
    if export_paid is not None and export_market is not None:
        parts.append((export_paid.avg - export_market) * export_paid.energy)
    return sum(parts) if parts else None
