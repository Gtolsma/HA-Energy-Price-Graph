# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.6.0] - 2026-09-28

### Added

- Markers in the price graph: a dashed line at the current time (on by default), a dotted line at the average price, the cheapest hours of each day as a green band (choose how many, off by default) and negative prices as a red area with a zero line (on by default). They are kept out of the tooltip.
- Upcoming prices for Nord Pool, Tibber, EnergyZero and easyEnergy in Home Assistant core, which offer them through an action instead of sensor attributes. The integration calls the action and caches the result for 15 minutes.
- The price sensor itself is now used for upcoming prices when no forecast sensor is chosen (option *Use the price sensor itself*, on by default), so Nord Pool, ENTSO-e and similar sensors show their forecast without extra setup.
- Forecast options to read only one attribute and to name the field with the price, for sensors whose format is not detected.
- Average price card: *Timing* shows the share of your import in the cheapest and the most expensive quarter of the hours of each day (periods up to 35 days).
- Average price card: optional surcharge per kWh on the market import and export price (for example energy tax and your supplier's markup), for when your costs include them but the price sensor does not.
- Sensors with the average import and export price you paid / received, the average market prices and the result compared with the market, for today and this month.
- The margin for the colour of the current price is now an option (default 10 %).
- The gas price graph can also be shown on the Summary tab.
- A repair message when the price graph cannot be added to the Energy dashboard (for example after a Home Assistant update changed the frontend internals). It disappears by itself once the graph works again.
- A repair message when no price sensor is found in the Energy settings.
- Diagnostics (options, price sensors found, status of the frontend module) to attach to bug reports.
- German translation of the setup and options.
- Tests for the calculations in the frontend module (`npm test`), ESLint and ruff, all run on GitHub for every push.

### Fixed

- Average price card: hours with a negative price were counted as a positive cost, so your average import price, export price and the result compared with the market were wrong on days with negative prices. The sign of the cost is now kept.
- Colour of the current price: on days with prices around zero almost every price was shown as red or green, because the difference was measured relative to an average close to zero. It is now measured against the average or half of today's price range, whichever is larger.
- Upcoming prices: for items with several unknown numbers, any number could be taken as the price. Now a field is only guessed when it is the only other number in the item.
- The log line when no price sensor is found is now described correctly in the README.

### Changed

- The option *Show result in euros* is renamed to *Show result as an amount*; the amount was already shown in the currency of your Home Assistant.
- The stray `download` file in the root of the repository is removed.

## [1.5.3] - 2026-09-24

### Changed

- Average price card: the result compared with the market average is now shown in euros for import and export separately, and the total is labelled *Result vs market* with a + or − sign. Previously only the total was shown as *Saved* or *Paid extra*, which was misleading when most of the difference came from export (for example with solar panels, where you mostly export when prices are low).
- The option *Show savings* is renamed to *Show result in euros*.

## [1.5.2] - 2026-09-24

### Fixed

- Repository clean-up: copies of the integration files had ended up in the root of the repository, which made the automatic hassfest and test checks fail. They have been removed, so the checks pass again for this release.

This is a maintenance release: the integration itself is identical to 1.5.1, so updating is optional.

## [1.5.1] - 2026-09-24

### Fixed

- After an update, open browser tabs kept running the old version until a hard refresh. The integration now registers a small loader that is never cached and always imports the installed version, and an open tab reloads itself once when it notices a newer version.
- Gas tab: the price graph is placed below the gas consumption graph and its totals table, so these stay side by side.

### Changed

- The colour of the current price compares with today's average price instead of the last 24 hours. With a forecast sensor the whole day, including upcoming prices, is used.
- The options form is grouped: Price graph, Current price, Average price, Gas, Forecast and Advanced.

## [1.5.0] - 2026-09-24

### Added

- Resolution *Auto (fine)*, the new default for new installations: 5-minute statistics for periods up to a week, so quarter-hour prices change exactly at :00, :15, :30 and :45; hourly or daily averages for longer periods. Falls back to hourly averages when there are no 5-minute statistics.
- Current price chips are coloured green, orange or red compared to the average of the last 24 hours (option *Colour the current price*).
- Savings compared to the market average in the average price card (option *Show savings*).
- Upcoming prices as a dashed line, from forecast sensors chosen in the new *Forecast* section of the options (import, export and gas). Nord Pool, ENTSO-e, Zonneplan and Frank Energie style attributes are recognised.
- Gas price graph on the Gas tab (option *Show gas price*), with current price chip.

### Changed

- The options form groups the forecast sensors and the overrides (title, sensors, names) in collapsible sections.

## [1.4.1] - 2026-09-23

### Fixed

- Average price card could stay empty until a hard browser refresh when Home Assistant rebuilt the view; it now keeps and recalculates its data.
- Average price card retries loading the market average when the recorder is not ready yet (for example right after a restart).
- Average price is now calculated only over periods in which both energy and cost were recorded, so a sensor added or repaired halfway through a day no longer produces an impossible price.
- Market average for export is also shown when import and export use the same price sensor.

### Changed

- The average price card no longer depends on the price graph being shown on the Electricity tab; it also works without price sensors and then shows a fixed price, if configured, as the market value.

## [1.4.0] - 2026-09-23

### Added

- Average price card below *Energy distribution* on the Electricity tab. Shows, for the selected period, what you actually paid for import and received for export per kWh (cost ÷ energy), next to the average market price, with the difference in percent. Can be turned off with the new *Show average price* option.

## [1.3.0] - 2026-09-23

### Changed

- Option changes no longer need a browser refresh: the frontend module reads the options over the websocket API each time the Energy dashboard is opened. The module URL only changes when the integration is updated.

## [1.2.2] - 2026-09-23

### Fixed

- CI: pin the test dependencies (`pytest-homeassistant-custom-component` and the matching `home-assistant-frontend`) so the tests run reliably. No functional changes to the integration.

## [1.2.1] - 2026-09-23

### Fixed

- CI: install the Home Assistant frontend package for the tests; update GitHub Actions to Node 24 versions.

## [1.2.0] - 2026-09-23

### Added

- Current import and export price as small chips in the header of the price graph (like the kWh total on the energy usage graph). Can be turned off with the new *Show current price* option.

### Changed

- Default line style is now *Straight*. Installations that never changed the line style switch from *Stepped* to *Straight*; pick *Stepped* under Configure to keep it.

## [1.1.0] - 2026-09-23

### Added

- Line style option: *Stepped* (exact price per period, new default), *Straight* or *Smooth*.

### Fixed

- The graph could be missing when the frontend replaces the custom element registry at start-up; the strategies are now hooked more reliably.
- Support for older Home Assistant versions whose Energy views use a flat card layout instead of sections.
- Resolution *Auto* no longer breaks the graph on frontends that do not know the `auto` period.

## [1.0.0] - 2026-09-23

### Added

- Electricity price graph on the built-in Energy dashboard (Electricity and Summary tabs), synced with the Energy date picker.
- Import and export price as separate lines, read automatically from the Energy settings.
- Options flow: resolution, tabs, export line, min/max, title, sensor overrides and line names.
- English, Dutch and German default labels; English and Dutch UI translations.
- Integration icon (`brand/`), shown in Home Assistant 2026.3 and newer.

[1.5.3]: https://github.com/Gtolsma/HA-Energy-Price-Graph/compare/1.5.2...1.5.3
[1.5.2]: https://github.com/Gtolsma/HA-Energy-Price-Graph/compare/1.5.1...1.5.2
[1.5.1]: https://github.com/Gtolsma/HA-Energy-Price-Graph/compare/1.5.0...1.5.1
[1.5.0]: https://github.com/Gtolsma/HA-Energy-Price-Graph/compare/1.4.1...1.5.0
[1.4.1]: https://github.com/Gtolsma/HA-Energy-Price-Graph/compare/1.4.0...1.4.1
[1.4.0]: https://github.com/Gtolsma/HA-Energy-Price-Graph/compare/1.3.0...1.4.0
[1.3.0]: https://github.com/Gtolsma/HA-Energy-Price-Graph/compare/1.2.2...1.3.0
[1.2.2]: https://github.com/Gtolsma/HA-Energy-Price-Graph/compare/1.2.1...1.2.2
[1.2.1]: https://github.com/Gtolsma/HA-Energy-Price-Graph/compare/1.2.0...1.2.1
[1.2.0]: https://github.com/Gtolsma/HA-Energy-Price-Graph/compare/1.1.0...1.2.0
[1.1.0]: https://github.com/Gtolsma/HA-Energy-Price-Graph/compare/1.0.0...1.1.0
[1.0.0]: https://github.com/Gtolsma/HA-Energy-Price-Graph/releases/tag/1.0.0
