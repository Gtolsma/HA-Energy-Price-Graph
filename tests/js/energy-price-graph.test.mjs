// Tests for the pure functions of the frontend module.
// Run with `npm test` (sets TZ=Europe/Amsterdam, so day boundaries are fixed).
import assert from "node:assert/strict";
import { describe, it } from "node:test";

import {
  cheapestHourSet,
  finePeriod,
  forecastPoints,
  forecastScale,
  gridStatIds,
  levelFor,
  marketPeriod,
  paidAverage,
  runData,
  savings,
  timeWeightedMean,
  timingShares,
  withForecast,
  withOverlays,
} from "../../custom_components/energy_price_graph/frontend/energy-price-graph.js";

const HOUR = 3600000;
const T0 = Date.parse("2026-09-28T00:00:00+02:00"); // local midnight

/** Hourly points for a whole day with the given prices. */
function day(prices, start = T0) {
  return prices.map((v, i) => [start + i * HOUR, v]);
}

describe("paidAverage", () => {
  const flows = [{ energy: "sensor.energy", cost: "sensor.cost" }];
  const stats = (energy, cost) => ({
    stats: {
      "sensor.energy": energy.map((change, i) => ({ start: i, change })),
      "sensor.cost": cost.map((change, i) => ({ start: i, change })),
    },
  });

  it("divides cost by energy", () => {
    const r = paidAverage(stats([1, 3], [0.2, 0.6]), flows);
    assert.equal(r.energy, 4);
    assert.ok(Math.abs(r.avg - 0.2) < 1e-9);
  });

  it("keeps the sign of the cost at negative prices", () => {
    // 1 kWh at +0.30 and 1 kWh at -0.10: on average 0.10 per kWh, not 0.20.
    const r = paidAverage(stats([1, 1], [0.3, -0.1]), flows);
    assert.ok(Math.abs(r.avg - 0.1) < 1e-9);
  });

  it("skips periods without cost or without energy", () => {
    const data = {
      stats: {
        "sensor.energy": [{ start: 0, change: 1 }, { start: 1, change: 2 }, { start: 2, change: 0 }],
        "sensor.cost": [{ start: 0, change: 0.25 }, { start: 2, change: 5 }],
      },
    };
    const r = paidAverage(data, flows);
    assert.equal(r.energy, 1);
    assert.equal(r.avg, 0.25);
  });

  it("returns null without cost statistic", () => {
    assert.equal(paidAverage(stats([1], [1]), [{ energy: "sensor.energy", cost: null }]), null);
  });
});

describe("savings", () => {
  it("is positive when you did better than the market", () => {
    const s = savings({
      importPaid: 0.2, importMarket: 0.25, importEnergy: 10,
      hasExport: true, exportPaid: 0.05, exportMarket: 0.1, exportEnergy: 4,
    });
    assert.ok(Math.abs(s.import - 0.5) < 1e-9);
    assert.ok(Math.abs(s.export + 0.2) < 1e-9);
    assert.ok(Math.abs(s.total - 0.3) < 1e-9);
  });

  it("is null without data", () => {
    assert.deepEqual(savings({ importPaid: null, importMarket: null, hasExport: false }), {
      import: null, export: null, total: null,
    });
  });
});

describe("gridStatIds", () => {
  it("reads the older schema and cost sensors", () => {
    const prefs = {
      energy_sources: [
        {
          type: "grid",
          flow_from: [{ stat_energy_from: "sensor.in", stat_cost: null, number_energy_price: 0.3 }],
          flow_to: [{ stat_energy_to: "sensor.out", stat_compensation: "sensor.comp" }],
        },
      ],
    };
    const out = gridStatIds(prefs, { cost_sensors: { "sensor.in": "sensor.in_cost" } });
    assert.deepEqual(out.from, [{ energy: "sensor.in", cost: "sensor.in_cost" }]);
    assert.deepEqual(out.to, [{ energy: "sensor.out", cost: "sensor.comp" }]);
    assert.equal(out.fixedImport, 0.3);
  });

  it("reads the current schema", () => {
    const prefs = {
      energy_sources: [
        { type: "grid", stat_energy_from: "sensor.in", stat_cost: "sensor.c", stat_energy_to: "sensor.out", number_energy_price_export: 0.07 },
      ],
    };
    const out = gridStatIds(prefs, {});
    assert.deepEqual(out.from, [{ energy: "sensor.in", cost: "sensor.c" }]);
    assert.equal(out.to[0].energy, "sensor.out");
    assert.equal(out.fixedExport, 0.07);
  });
});

describe("forecastPoints", () => {
  it("reads Nord Pool raw_today / raw_tomorrow", () => {
    const state = {
      attributes: {
        raw_today: [{ start: "2026-09-28T00:00:00+02:00", end: "2026-09-28T01:00:00+02:00", value: 0.2 }],
        raw_tomorrow: [{ start: "2026-09-29T00:00:00+02:00", end: "2026-09-29T01:00:00+02:00", value: 0.3 }],
      },
    };
    assert.deepEqual(forecastPoints(state).map(([, v]) => v), [0.2, 0.3]);
  });

  it("reads Zonneplan's electricity_price among other numbers", () => {
    const state = { attributes: { forecast: [{ datetime: "2026-09-28T10:00:00Z", electricity_price: 2500000, sustainability_score: 7 }] } };
    assert.deepEqual(forecastPoints(state), [[Date.parse("2026-09-28T10:00:00Z"), 2500000]]);
  });

  it("does not guess between several unknown numbers", () => {
    const state = { attributes: { items: [{ start: "2026-09-28T10:00:00Z", a: 1, b: 2 }] } };
    assert.deepEqual(forecastPoints(state), []);
  });

  it("uses a single unknown number", () => {
    const state = { attributes: { items: [{ start: "2026-09-28T10:00:00Z", end: "2026-09-28T11:00:00Z", eur: 0.4 }] } };
    assert.deepEqual(forecastPoints(state).map(([, v]) => v), [0.4]);
  });

  it("honours the attribute and field options", () => {
    const state = {
      attributes: {
        today: [{ start: "2026-09-28T10:00:00Z", price: 1, price_excl: 0.8 }],
        tomorrow: [{ start: "2026-09-29T10:00:00Z", price: 2, price_excl: 1.6 }],
      },
    };
    assert.deepEqual(forecastPoints(state, "tomorrow").map(([, v]) => v), [2]);
    assert.deepEqual(forecastPoints(state, null, "price_excl").map(([, v]) => v), [0.8, 1.6]);
  });
});

describe("forecastScale", () => {
  it("scales cents, €/MWh and Zonneplan units to €/kWh", () => {
    assert.equal(forecastScale([[0, 25]], 0.25), 0.01);
    assert.equal(forecastScale([[0, 250]], 0.25), 0.001);
    assert.equal(forecastScale([[0, 2500000]], 0.25), 1e-7);
    assert.equal(forecastScale([[0, 0.24]], 0.25), 1);
  });
});

describe("withForecast", () => {
  it("adds a dashed line from the running period on", () => {
    const now = Date.now();
    const hass = {
      states: {
        "sensor.price": { state: "0.25", attributes: {} },
        "sensor.fc": {
          state: "0.25",
          attributes: {
            prices: [
              { start: new Date(now - HOUR).toISOString(), price: 20 },
              { start: new Date(now - 1000).toISOString(), price: 25 },
              { start: new Date(now + HOUR).toISOString(), price: 30 },
            ],
          },
        },
      },
    };
    const data = [{ id: "sensor.price-mean", type: "line", data: [], xAxisIndex: 1 }];
    const out = withForecast(data, [{ entity: "sensor.fc", reference: "sensor.price", name: "f", color: "#000" }], hass, "stepped");
    assert.equal(out.length, 2);
    assert.equal(out[1].id, "epg-forecast-0");
    assert.equal(out[1].xAxisIndex, 1);
    assert.equal(out[1].step, "end");
    assert.deepEqual(out[1].data.map(([, v]) => v), [0.25, 0.3]);
  });
});

describe("levelFor", () => {
  const stats = { avg: 0.25, min: 0.2, max: 0.3 };

  it("compares with the average", () => {
    assert.equal(levelFor(0.2, stats, "low", 0.1), "good");
    assert.equal(levelFor(0.25, stats, "low", 0.1), "mid");
    assert.equal(levelFor(0.3, stats, "low", 0.1), "bad");
    assert.equal(levelFor(0.3, stats, "high", 0.1), "good");
  });

  it("stays sensible when the average is close to zero", () => {
    // Average 0.005, prices from -0.05 to 0.15: 0.01 is about average, not
    // "100 % more expensive".
    const s = { avg: 0.005, min: -0.05, max: 0.15 };
    assert.equal(levelFor(0.01, s, "low", 0.1), "mid");
    assert.equal(levelFor(-0.04, s, "low", 0.1), "good");
    assert.equal(levelFor(0.12, s, "low", 0.1), "bad");
  });

  it("uses the threshold", () => {
    assert.equal(levelFor(0.27, stats, "low", 0.1), "mid");
    assert.equal(levelFor(0.27, stats, "low", 0.05), "bad");
  });

  it("returns null without data", () => {
    assert.equal(levelFor(0.2, null, "low", 0.1), null);
    assert.equal(levelFor(0.2, { avg: 0, min: 0, max: 0 }, "low", 0.1), null);
  });
});

describe("timeWeightedMean", () => {
  it("weights each price by how long it holds", () => {
    // 0.1 for 1 hour, then 0.4 for 3 hours (single point at the end holds a step)
    const points = [[0, 0.1], [HOUR, 0.4], [2 * HOUR, 0.4], [3 * HOUR, 0.4]];
    assert.ok(Math.abs(timeWeightedMean(points) - 0.325) < 1e-9);
    assert.equal(timeWeightedMean([]), null);
  });
});

describe("cheapestHourSet", () => {
  it("picks the cheapest hours of a complete day", () => {
    const prices = Array.from({ length: 24 }, (_, i) => 0.3 - (i === 3 ? 0.2 : 0) - (i === 14 ? 0.25 : 0));
    const set = cheapestHourSet(day(prices), 2);
    assert.deepEqual([...set].sort((a, b) => a - b), [T0 + 3 * HOUR, T0 + 14 * HOUR]);
  });

  it("combines quarter-hour prices into hours", () => {
    const points = [];
    for (let i = 0; i < 24 * 4; i++) points.push([T0 + i * HOUR / 4, i >= 40 && i < 44 ? 0.01 : 0.3]);
    assert.deepEqual([...cheapestHourSet(points, 1)], [T0 + 10 * HOUR]);
  });

  it("skips days that are not (almost) complete", () => {
    assert.equal(cheapestHourSet(day([0.1, 0.2, 0.3]), 1).size, 0);
  });
});

describe("runData", () => {
  it("ends each run at the next point", () => {
    const points = day([1, 2, 3, 4]);
    const out = runData(points, (t) => t === T0 + HOUR);
    assert.deepEqual(out, [[T0 + HOUR, 2], [T0 + 2 * HOUR, 2], [T0 + 2 * HOUR, null]]);
  });
});

describe("withOverlays", () => {
  const colors = { good: "#0f0", bad: "#f00", muted: "#888" };
  const series = (prices) => [{ id: "sensor.price-mean", type: "line", xAxisIndex: 1, data: day(prices) }];
  const ids = (out) => out.map((s) => s.id).filter((id) => id.startsWith("epg-overlay-"));

  it("adds the now line, average line and cheapest hours", () => {
    const prices = Array.from({ length: 24 }, (_, i) => 0.2 + i / 100);
    const ov = { reference: "sensor.price", now: true, average: true, cheapest: 3, negative: true, colors };
    const out = withOverlays(series(prices), ov, "stepped", T0 + 12 * HOUR);
    assert.deepEqual(ids(out).sort(), ["epg-overlay-average", "epg-overlay-cheapest", "epg-overlay-now"]);
    const now = out.find((s) => s.id === "epg-overlay-now");
    assert.deepEqual(now.data.map(([t]) => t), [T0 + 12 * HOUR, T0 + 12 * HOUR]);
    assert.ok(Math.abs(now.data[0][1] - 0.2) < 1e-9 && Math.abs(now.data[1][1] - 0.43) < 1e-9);
    assert.equal(now.xAxisIndex, 1);
    assert.deepEqual(now.tooltip, { show: false });
    // The cheapest hours (00:00-03:00) are a band up to the top of the graph.
    const cheapest = out.find((s) => s.id === "epg-overlay-cheapest");
    assert.deepEqual(cheapest.data.map(([t]) => t), [T0, T0 + HOUR, T0 + 2 * HOUR, T0 + 3 * HOUR, T0 + 3 * HOUR]);
    assert.ok(cheapest.data.slice(0, 4).every(([, v]) => Math.abs(v - 0.43) < 1e-9));
    assert.equal(cheapest.data[4][1], null);
  });

  it("highlights negative prices with a zero line", () => {
    const prices = Array.from({ length: 24 }, (_, i) => (i === 13 ? -0.05 : 0.1));
    const ov = { reference: "sensor.price", now: false, average: false, cheapest: 0, negative: true, colors };
    const out = withOverlays(series(prices), ov, "straight");
    assert.deepEqual(ids(out).sort(), ["epg-overlay-negative", "epg-overlay-zero"]);
    const negative = out.find((s) => s.id === "epg-overlay-negative");
    assert.equal(negative.data[13][1], -0.05);
    assert.equal(negative.data[0][1], 0);
  });

  it("adds nothing when everything is off or there is no data", () => {
    const ov = { reference: "sensor.price", now: false, average: false, cheapest: 0, negative: true, colors };
    assert.equal(withOverlays(series([0.1, 0.2]), ov, "straight").length, 1);
    assert.equal(withOverlays([{ id: "sensor.price-mean", type: "line", data: [] }], { ...ov, now: true }).length, 1);
  });

  it("includes upcoming prices", () => {
    const measured = [{ id: "sensor.price-mean", type: "line", data: day(Array(12).fill(0.3)) }];
    const forecast = {
      id: "epg-forecast-0",
      type: "line",
      epgReference: "sensor.price",
      data: day(Array(12).fill(0.1), T0 + 12 * HOUR),
    };
    const ov = { reference: "sensor.price", now: false, average: true, cheapest: 0, negative: false, colors };
    const out = withOverlays([...measured, forecast], ov, "stepped");
    const avg = out.find((s) => s.id === "epg-overlay-average");
    assert.ok(Math.abs(avg.data[0][1] - 0.2) < 1e-9);
  });
});

describe("timingShares", () => {
  it("measures the share of energy in cheap and expensive hours", () => {
    const prices = new Map(day(Array.from({ length: 24 }, (_, i) => i)));
    const energy = new Map([
      [T0, 3], // cheapest hour
      [T0 + 23 * HOUR, 1], // most expensive hour
      [T0 + 12 * HOUR, 4],
    ]);
    const r = timingShares(energy, prices);
    assert.equal(r.energy, 8);
    assert.equal(r.cheap, 3 / 8);
    assert.equal(r.expensive, 1 / 8);
  });

  it("returns null without energy", () => {
    assert.equal(timingShares(new Map(), new Map(day([1, 2, 3, 4]))), null);
  });
});

describe("periods", () => {
  const now = Date.parse("2026-09-28T12:00:00Z");
  it("finePeriod follows the range and recorder history", () => {
    assert.equal(finePeriod(new Date(now - 86400000), null, now), "5minute");
    assert.equal(finePeriod(new Date(now - 20 * 86400000), new Date(now - 19 * 86400000), now), "hour");
    assert.equal(finePeriod(new Date(now - 30 * 86400000), null, now), "hour");
    assert.equal(finePeriod(new Date(now - 200 * 86400000), null, now), "day");
    assert.equal(finePeriod(new Date(now - 800 * 86400000), null, now), "month");
  });

  it("marketPeriod uses hours up to 35 days", () => {
    assert.equal(marketPeriod(new Date(now - 30 * 86400000), null, new Date(now)), "hour");
    assert.equal(marketPeriod(new Date(now - 60 * 86400000), null, new Date(now)), "day");
  });
});
