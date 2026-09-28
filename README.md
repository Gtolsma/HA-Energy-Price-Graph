# Energy Price Graph for Home Assistant

Show your **dynamic electricity price** directly in the **built-in Energy dashboard** of Home Assistant, right below the energy usage graph.

![Electricity price graph on the Energy dashboard, with the current import and export price in the header](https://raw.githubusercontent.com/Gtolsma/HA-Energy-Price-Graph/main/docs/images/price-graph.png)

- Import price and (optionally) export / feed-in price as two lines in one graph
- Current import and export price as chips in the card header, coloured green / orange / red compared to today's average
- Markers in the graph: a line at the current time, the average price, the cheapest hours of the day and negative prices
- Average price card on the Electricity tab: what you actually paid / received per kWh next to the average market price, the result as an amount and your timing (how much you used in cheap and expensive hours)
- Upcoming prices as a dashed line: from the price sensor itself, a forecast sensor you choose, or the action of Nord Pool, Tibber, EnergyZero and easyEnergy
- Sensors with your average prices and the result compared with the market, for today and this month
- Gas price graph on the Gas tab and, optionally, the Summary tab
- Follows the Energy dashboard date picker (today, yesterday, last week, …)
- Uses the price sensors you already configured in the Energy settings, so no extra setup is needed
- Colours match the grid import / export colours of the Energy dashboard
- Configurable from the UI: resolution, line style, tabs, markers, min/max, title, sensor overrides
- A repair message when a Home Assistant update breaks the graph or no price sensor is set, and diagnostics for bug reports

### Average price

On the Electricity tab, below *Energy distribution*, a card compares what you actually paid for import and received for export per kWh with the average market price for the selected period.

<img src="https://raw.githubusercontent.com/Gtolsma/HA-Energy-Price-Graph/main/docs/images/average-price.png" alt="Average price card: your average import and export price next to the market average" width="400">

> Home Assistant has no official way to add cards to the built-in Energy dashboard. This integration fills that gap until the feature exists in Home Assistant itself.

## Requirements

- Home Assistant 2025.8 or newer (tested on 2026.x); the integration icon is shown from 2026.3
- A price sensor configured in **Settings → Dashboards → Energy → Electricity grid**:
  - *Costs*: "Use an entity with current price"
  - *Compensation* (optional): "Use an entity with current price"
- The price sensor needs long-term statistics (`state_class: measurement`). Most price integrations provide this already.

## Installation

### HACS (custom repository)

1. HACS → ⋮ → **Custom repositories**
2. Add `https://github.com/Gtolsma/HA-Energy-Price-Graph` with type **Integration**
3. Search for **Energy Price Graph**, download it and restart Home Assistant
4. **Settings → Devices & services → Add integration → Energy Price Graph**
5. Refresh your browser once

### Manual

1. Copy `custom_components/energy_price_graph` to `/config/custom_components/energy_price_graph`
2. Restart Home Assistant and add the integration as in step 4 above
3. Refresh your browser once

## Options

Go to **Settings → Devices & services → Energy Price Graph → Configure**. The options are grouped in *Price graph*, *Markers in the graph*, *Current price*, *Average price*, *Gas*, *Forecast* and *Advanced*.

| Option | Default | Description |
|---|---|---|
| Resolution | Auto (fine) | `Auto (fine)` shows every price step for periods up to a week: it uses 5-minute statistics, so quarter-hour prices change exactly at :00, :15, :30 and :45. Longer or older periods use hourly or daily averages. 5-minute statistics are kept as long as your recorder keeps history (`purge_keep_days`, default 10 days); without them the graph falls back to hourly averages. `Auto` uses hourly averages for a day. |
| Line style | Straight | `Straight` connects the points directly. `Stepped` shows the exact price per period (a price holds for the whole quarter or hour). `Smooth` draws a rounded curve like the standard statistics graph. |
| Show the price graph on tabs | Electricity, Summary | Energy dashboard tabs where the electricity price graph is added. The Summary tab only exists when you track more than one energy type or have a grid power sensor. |
| Show export price | On | Adds a second line when the export price is a different sensor than the import price. |
| Show min/max per period | Off | Also draws the lowest and highest price within each period. |
| Show a line at the current time | On | Vertical dashed line at the current time when the selected period includes now. |
| Show the average price as a line | Off | Horizontal dotted line at the average import price of the period shown, including upcoming prices. |
| Highlight the cheapest hours per day | 0 (off) | Shades the N cheapest hours of each day, for example to plan the washing machine or charging. Only days of which at least 20 hours of prices are known are marked, so with a forecast also today and tomorrow. Only at a resolution of an hour or finer. |
| Highlight negative prices | On | Shades the area below zero and draws a zero line when the price is negative. |
| Show current price | On | Small chips in the card header with the current price. |
| Colour the current price | On | Green when the current price is favourable compared to today's average price (low for import and gas, high for export), orange around the average, red when unfavourable. With a forecast the average covers the whole day, including the upcoming prices; otherwise the prices recorded so far today are used (so there is no colour in the first hour after midnight). |
| Margin around the average | 10 % | How far the price may differ from today's average and still count as average (orange). The difference is measured against the average price or, when prices are close to zero, against half of today's price range, so a price of 1 ct on a day that averages 0.5 ct is not shown as "twice as expensive". |
| Show average price | On | Card below *Energy distribution* on the Electricity tab. **You**: what you actually paid (import) or received (export) per kWh in the selected period, calculated as cost ÷ energy from the Energy dashboard statistics. **Market**: the plain average of the price sensor over the same period plus the surcharge below (or your fixed price, if you use one). Only periods in which both energy and cost were recorded are counted; hours with a negative price count as negative cost. The percentage shows how you did compared to the market (green is better). |
| Show result as an amount | On | Shows in the average price card how much better (+) or worse (−) you did than the market average, in your currency: for import (market price − your price) × kWh bought, for export (your price − market price) × kWh sold, and the total. With solar panels the export part is usually negative, because you export mostly around midday when prices are low. |
| Show timing | On | Share of your import in the cheapest and the most expensive quarter of the hours of each day, for periods up to 35 days. With evenly spread use both are about 25 %; a higher first number means you shifted your use to cheap hours. |
| Surcharge on market import / export price | 0 | Added per kWh to the average of the price sensor, for example energy tax and your supplier's markup, when your cost statistics include them but the price sensor only has the bare market price. Can be negative. |
| Show gas price | On | Gas price graph, using the gas price sensor from your Energy settings. |
| Show the gas price graph on tabs | Gas | On the Gas tab it is placed below the gas consumption graph; on the Summary tab below the electricity price graph. |
| **Forecast** section | – | Upcoming prices are drawn as a dashed line from now on; select tomorrow in the date picker to see tomorrow. With *Use the price sensor itself* (on by default) the price sensor is used when no forecast sensor is chosen. The upcoming prices are read from the attributes of the sensor, with formats such as Nord Pool (`raw_today` / `raw_tomorrow`), ENTSO-e (`prices`), Zonneplan (`forecast`) and Frank Energie (`prices`). For **Nord Pool, Tibber, EnergyZero and easyEnergy** in Home Assistant, which offer the prices through an action instead, the integration calls that action (cached for 15 minutes). Values in cents, per MWh or smaller units are scaled automatically to the unit of your price sensor. If the prices are not found, set the *attribute* (for example `raw_tomorrow`) and/or the *field* with the price (for example `price_incl_vat`). |
| **Advanced** section | – | Card title, sensors to use instead of the ones in your Energy settings (import, export, gas) and the legend names of the import and export lines. |

Changes apply the next time you open the Energy dashboard; no browser refresh is needed. After an update of the integration, an open browser tab reloads itself once when you open the Energy dashboard (from version 1.5.1 on).

## Sensors

The integration adds a service device *Energy Price Graph* with these sensors, updated every 15 minutes from the same statistics as the average price card:

| Sensor | Description |
|---|---|
| Average import price paid today / this month | What you paid per kWh (cost ÷ energy) |
| Average market import price today / this month | Average of the import price sensor, plus the surcharge |
| Average export price received today / this month | What you received per kWh |
| Average market export price today / this month | Average of the export price sensor, plus the surcharge |
| Result vs market today / this month | How much better (+) or worse (−) you did than the market average, in your currency |

The export sensors are unavailable without export in your Energy settings. Use them in automations, notifications or your own dashboards; their history is kept in the long-term statistics.

## How it works

The Energy dashboard is generated in the frontend by "view strategies". This integration serves a small JavaScript module and registers it with the frontend. The module reads the integration's options over the websocket API each time the Energy dashboard is built. The module extends the output of the Electricity and Summary strategies with a standard `statistics-graph` card configured with `energy_date_selection: true`, so it stays in sync with the dashboard's date picker.

The graph does not appear in the Energy dashboard's **Customize cards** dialog; use the integration options instead.

## Limitations

- This relies on **internal frontend code** of Home Assistant, not a public API. A future Home Assistant update may break it. If that happens, the Energy dashboard keeps working normally, just without the price graph, and a repair message appears in **Settings → Repairs**. Please open an issue.
- No water prices.

## Troubleshooting

- **Settings → Repairs** shows a message when the graph could not be added (usually after a Home Assistant update) or when no price sensor is found. The first one disappears by itself once the graph works again.
- **Settings → Devices & services → Energy Price Graph → ⋮ → Download diagnostics** gives a file with the options, the price sensors found in your Energy settings (names, units and attribute names, no history) and the last status of the frontend module. Please attach it to an issue.
- Open the browser console (F12) and look for lines starting with `[energy-price-graph]`:
  - `active on electricity` / `active on overview`: the module is loaded.
  - `no price sensor found, no price graph added`: no price entity is configured in the Energy settings and no override is set.

## Migrating from the `www` script

If you previously used `energy-price-injector.js` via `frontend: extra_module_url`, remove that entry from `configuration.yaml` and delete the file from `/config/www/`.

## Development

Python (integration) and JavaScript (frontend module) each have their own tests and linter:

```bash
pip install -r requirements_test.txt ruff
pytest
ruff check . && ruff format --check .

npm ci
npm test       # node --test, for the calculations in the frontend module
npm run lint   # ESLint
```

The same checks run on GitHub for every push, together with hassfest and the HACS validation.

## Versioning and releases

This project uses [Semantic Versioning](https://semver.org/) (`MAJOR.MINOR.PATCH`) and keeps a [CHANGELOG](CHANGELOG.md). HACS installs the zip attached to each GitHub release and offers updates when a new release is published.

To release a new version:

1. Bump `version` in `custom_components/energy_price_graph/manifest.json` (for example `1.0.0` → `1.1.0`).
2. Add a section for the new version with its date at the top of `CHANGELOG.md` (for example `## [1.1.0] - 2026-10-01`).
3. Commit and push: `git commit -am "Release 1.1.0" && git push`
4. On GitHub, go to **Releases → Draft a new release**, create tag `1.1.0` and publish it.

The release workflow checks that the tag, `manifest.json` and `CHANGELOG.md` agree, then builds `energy_price_graph.zip` and attaches it to the release.

## License

MIT
