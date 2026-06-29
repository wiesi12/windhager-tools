# TODO

## Core Library

### Discovery

- [x] Discover modules
- [x] Discover functions
- [x] Discover lookups
- [x] Discover NV's (LON network variables)
- [x] Read XML resources (EbenenTexte, VarIdentTexte)
- [x] Multi-language resource support (de/en/fr/it)
- [x] Build OID map (including NV entries)
- [x] Fix lookup-name collisions across function types (fcttyp)

### Models

- [x] Complete Entry model
- [x] NvEntry model
- [ ] Typed value helpers
- [ ] Enum helper methods

### Catalog

- [x] Save catalog
- [x] Load catalog
- [x] Per-language catalog caching
- [x] Store catalog inside the integration directory (persistent_directory)
- [ ] Catalog versioning / schema migration

### Diagnostics

- [x] Statistics
- [x] Validation
- [ ] Unknown type report
- [ ] Unknown unit report
- [ ] Unknown subtype report
- [ ] Firmware capability report

### Polling

- [x] Poll OIDs
- [x] Poll NV's (separate, slower interval to limit extra API load)
- [ ] Optimized/parallel polling
- [ ] Change detection

---

## Home Assistant

### Config Flow

- [x] Host
- [x] Username
- [x] Password (masked input)
- [ ] Select discovered modules
- [ ] Select sensor groups
- [ ] Reconfigure options (e.g. poll intervals)

### Sensor

- [x] Basic sensors
- [x] Metadata mapping (units, device classes, state classes)
- [x] Unit translation (Windhager-specific -> HA units, e.g. Std -> h)
- [x] Readable naming (lookup/entry name composition)
- [x] Readable names for known NV's, raw name fallback for unknown ones
- [x] Icons
- [x] Entity categories (diagnostic)
- [x] Device classes
- [x] State classes (measurement / total_increasing)
- [x] Date/time parsing (native date/time objects, not raw strings)
- [x] Stable, readable entity_ids (suggested_object_id)
- [x] Graceful handling of non-numeric placeholder values ("-")

### Number / Select

- [ ] Read/write values
- [ ] Min / Max / Step
- [ ] Lookup enums
- [ ] Write support

### Devices

- [x] Basic device per module
- [ ] Better device hierarchy
- [ ] Function-level devices

### Branding / Packaging

- [x] Custom icon/logo (brand/ directory)
- [x] Dark mode variants
- [x] manifest.json complete (issue_tracker, version, etc.)
- [x] hacs.json
- [x] Non-blocking NV first refresh (background task)
- [x] config_entry passed to coordinators

---

## Compatibility

- [x] MES INFINITY + InfoWIN Touch (RC7030, firmware S 1.0.2) - tested
- [ ] MES PLUS (older, non-Touch) - untested, likely compatible
- [ ] Newer firmware / comWinStack API - likely NOT compatible, untested
- [ ] Multiple firmware versions / automatic capability detection
- [ ] Missing XML entries handling
- [ ] Unknown modules handling

---

## Release / Project

- [x] Localization (entity names: de/en/fr/it)
- [x] README documentation
- [x] LICENSE (MIT)
- [x] Remove credentials from git history
- [x] First HACS-compatible release (v0.1.0)
- [ ] Unit tests
- [ ] Submit to HACS default store (after some real-world testing)
- [ ] Community forum post to find testers for other firmware/hardware generations

## Future

- [ ] Write support (temperature setpoints, modes)
- [ ] Config-flow options for selecting which modules/sensors to expose
- [ ] Parallelized/faster initial discovery (carefully, to avoid overloading the webserver)
- [ ] Refine NV group selection: currently a single "NV's" checkbox
      covers all ~200 NV entries per module (e.g. BioWIN) - too coarse
      for meaningful filtering. Individual per-NV selection isn't
      practical either since most NVs only have a cryptic raw name
      (no entry in nv_names.py). Revisit once more NV names are
      known/whitelisted, or find another sensible grouping
      (e.g. by snvt_name/category).
- [ ] Architecture simplification: move windhager_tools/ directly into
      custom_components/windhager_infowin/lib/ with relative imports
      from the start, eliminating tools/build_integration.py and the
      vendor/ copy step entirely. Only worthwhile now that
      windhager_tools is no longer used as a standalone pip package
      (decided 2026-06-29) - otherwise this is a bigger, separate
      refactor, best done on its own, not mixed with other changes.
