# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.5.1] - 2026-09-24

### Fixed

- After an update, open browser tabs kept running the old version until a hard refresh. The integration now registers a small loader that is never cached and always imports the installed version, and an open tab reloads itself once when it notices a newer version.
- Gas tab: the price graph is placed below the gas consumption graph and its totals table, so these stay side by side.

### Changed

- The colour of the current price compares with today's average price instead of the last 24 hours. With a forecast sensor the whole day, including upcoming prices, is used.

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
