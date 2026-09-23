# Energy Price Graph for Home Assistant

Show your **dynamic electricity price** directly in the **built-in Energy dashboard** of Home Assistant, right below the energy usage graph.

![Electricity price graph on the Energy dashboard, with the current import and export price in the header](https://raw.githubusercontent.com/Gtolsma/HA-Energy-Price-Graph/main/docs/images/price-graph.png)

- Import price and (optionally) export / feed-in price as two lines in one graph
- Current import and export price as chips in the card header, coloured green / orange / red compared to today's average
- Average price card on the Electricity tab: what you actually paid / received per kWh next to the average market price, and how much you saved
- Upcoming prices as a dashed line (from a forecast sensor you choose)
- Gas price graph on the Gas tab
- Follows the Energy dashboard date picker (today, yesterday, last week, …)
- Uses the price sensors you already configured in the Energy settings, so no extra setup is needed
- Colours match the grid import / export colours of the Energy dashboard
- Configurable from the UI: resolution, line style, tabs, min/max, title, sensor overrides

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

Go to **Settings → Devices & services → Energy Price Graph → Configure**. The options are grouped in *Price graph*, *Current price*, *Average price*, *Gas*, *Forecast* and *Advanced*.

| Option | Default | Description |
|---|---|---|
| Resolution | Auto (fine) | `Auto (fine)` shows every price step for periods up to a week: it uses 5-minute statistics, so quarter-hour prices change exactly at :00, :15, :30 and :45. Longer or older periods use hourly or daily averages. 5-minute statistics are kept as long as your recorder keeps history (`purge_keep_days`, default 10 days); without them the graph falls back to hourly averages. `Auto` uses hourly averages for a day. |
| Line style | Straight | `Straight` connects the points directly. `Stepped` shows the exact price per period (a price holds for the whole quarter or hour). `Smooth` draws a rounded curve like the standard statistics graph. |
| Show the price graph on tabs | Electricity, Summary | Energy dashboard tabs where the electricity price graph is added. The Summary tab only exists when you track more than one energy type or have a grid power sensor. |
| Show export price | On | Adds a second line when the export price is a different sensor than the import price. |
| Show current price | On | Small chips in the card header with the current price. |
| Colour the current price | On | Green when the current price is favourable compared to today's average price (low for import and gas, high for export), orange around the average (within 10 %), red when unfavourable. With a forecast sensor the average covers the whole day, including the upcoming prices; otherwise the prices recorded so far today are used (so there is no colour in the first hour after midnight). |
| Show average price | On | Card below *Energy distribution* on the Electricity tab. **You**: what you actually paid (import) or received (export) per kWh in the selected period, calculated as cost ÷ energy from the Energy dashboard statistics. **Market**: the plain average of the price sensor over the same period (or your fixed price, if you use one). Only periods in which both energy and cost were recorded are counted. The percentage shows how you did compared to the market (green is better). |
| Show savings | On | Adds to the average price card how much you saved (or paid extra) compared to the market average: (market − your price) × kWh for import plus (your price − market) × kWh for export. |
| Show gas price | On | Price graph on the Gas tab, below the gas consumption graph, using the gas price sensor from your Energy settings. |
| Show min/max per period | Off | Also draws the lowest and highest price within each period. |
| **Forecast** section | – | Sensors that have the upcoming prices in their attributes, for import, export and gas. Upcoming prices are drawn as a dashed line from now on; select tomorrow in the date picker to see tomorrow. Supported formats include Nord Pool (`raw_today` / `raw_tomorrow`), ENTSO-e (`prices`), Zonneplan (`forecast`) and Frank Energie (`prices`); values in cents or smaller units are scaled automatically to the unit of your price sensor. |
| **Advanced** section | – | Card title, sensors to use instead of the ones in your Energy settings (import, export, gas) and the legend names of the import and export lines. |

Changes apply the next time you open the Energy dashboard; no browser refresh is needed. After an update of the integration, an open browser tab reloads itself once when you open the Energy dashboard (from version 1.5.1 on).

## How it works

The Energy dashboard is generated in the frontend by "view strategies". This integration serves a small JavaScript module and registers it with the frontend. The module reads the integration's options over the websocket API each time the Energy dashboard is built. The module extends the output of the Electricity and Summary strategies with a standard `statistics-graph` card configured with `energy_date_selection: true`, so it stays in sync with the dashboard's date picker.

The graph does not appear in the Energy dashboard's **Customize cards** dialog; use the integration options instead.

## Limitations

- This relies on **internal frontend code** of Home Assistant, not a public API. A future Home Assistant update may break it. If that happens, the Energy dashboard keeps working normally, just without the price graph. Please open an issue.
- No water prices.

## Troubleshooting

Open the browser console (F12) and look for lines starting with `[energy-price-graph]`:

- `active on electricity` / `active on overview`: the module is loaded.
- `no price sensor found, nothing added`: no price entity is configured in the Energy settings and no override is set.

## Migrating from the `www` script

If you previously used `energy-price-injector.js` via `frontend: extra_module_url`, remove that entry from `configuration.yaml` and delete the file from `/config/www/`.

## Development

```bash
pip install -r requirements_test.txt
pytest
```

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
