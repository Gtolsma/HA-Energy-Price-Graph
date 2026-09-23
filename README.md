# Energy Price Graph for Home Assistant

Show your **dynamic electricity price** directly in the **built-in Energy dashboard** of Home Assistant, right below the energy usage graph.

- Import price and (optionally) export / feed-in price as two lines in one graph
- Follows the Energy dashboard date picker (today, yesterday, last week, …)
- Uses the price sensors you already configured in the Energy settings, so no extra setup is needed
- Colours match the grid import / export colours of the Energy dashboard
- Configurable from the UI: resolution, tabs, min/max, title, sensor overrides

> Home Assistant has no official way to add cards to the built-in Energy dashboard. This integration fills that gap until the feature exists in Home Assistant itself.

## Requirements

- Home Assistant 2025.8 or newer (tested on 2026.x)
- A price sensor configured in **Settings → Dashboards → Energy → Electricity grid**:
  - *Costs*: "Use an entity with current price"
  - *Compensation* (optional): "Use an entity with current price"
- The price sensor needs long-term statistics (`state_class: measurement`). Most price integrations provide this already.

## Installation

### HACS (custom repository)

1. HACS → ⋮ → **Custom repositories**
2. Add `https://github.com/GITHUB_USER/HA-Energy-Price-Graph` with type **Integration**
3. Search for **Energy Price Graph**, download it and restart Home Assistant
4. **Settings → Devices & services → Add integration → Energy Price Graph**
5. Refresh your browser (Ctrl+F5)

### Manual

1. Copy `custom_components/energy_price_graph` to `/config/custom_components/energy_price_graph`
2. Restart Home Assistant and add the integration as in step 4 above
3. Refresh your browser (Ctrl+F5)

## Options

Go to **Settings → Devices & services → Energy Price Graph → Configure**.

| Option | Default | Description |
|---|---|---|
| Resolution | Auto | `Auto` follows the selected date range. `5 minutes` shows every price step (quarter-hour prices), but short-term data is only kept as long as your recorder keeps history (`purge_keep_days`, default 10 days). |
| Show on tabs | Electricity, Summary | Energy dashboard tabs where the graph is added. The Summary tab only exists when you track more than one energy type or have a grid power sensor. |
| Show export price | On | Adds a second line when the export price is a different sensor than the import price. |
| Show min/max per period | Off | Also draws the lowest and highest price within each period. |
| Card title | Electricity price | Leave empty for the default (translated for English, Dutch and German). |
| Import / export price sensor | from Energy settings | Override the sensors used for the graph only. |
| Name of import / export line | Import / Export | Legend names. |

After saving, refresh your browser to see the changes.

## How it works

The Energy dashboard is generated in the frontend by "view strategies". This integration serves a small JavaScript module and registers it with the frontend. The module extends the output of the Electricity and Summary strategies with a standard `statistics-graph` card configured with `energy_date_selection: true`, so it stays in sync with the dashboard's date picker.

The graph does not appear in the Energy dashboard's **Customize cards** dialog; use the integration options instead.

## Limitations

- This relies on **internal frontend code** of Home Assistant, not a public API. A future Home Assistant update may break it. If that happens, the Energy dashboard keeps working normally, just without the price graph. Please open an issue.
- Only grid prices are shown (no gas or water prices).

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

## License

MIT
