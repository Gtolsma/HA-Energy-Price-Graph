# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

[Unreleased]: https://github.com/Gtolsma/HA-Energy-Price-Graph/compare/1.2.1...HEAD
[1.2.1]: https://github.com/Gtolsma/HA-Energy-Price-Graph/compare/1.2.0...1.2.1
[1.2.0]: https://github.com/Gtolsma/HA-Energy-Price-Graph/compare/1.1.0...1.2.0
[1.1.0]: https://github.com/Gtolsma/HA-Energy-Price-Graph/compare/1.0.0...1.1.0
[1.0.0]: https://github.com/Gtolsma/HA-Energy-Price-Graph/releases/tag/1.0.0
