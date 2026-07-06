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
- [x] Typed value helpers
- [x] Enum helper methods

### Catalog

- [x] Save catalog
- [x] Load catalog
- [x] Per-language catalog caching
- [x] Store catalog inside the integration directory (persistent_directory)
- [x] Catalog versioning / schema migration

### Diagnostics

- [x] Statistics
- [x] Validation
- [x] Unknown type/unit/subtype report
- [ ] Firmware capability report

### Polling

- [x] Poll OIDs
- [x] Poll NV's (separate, slower interval to limit extra API load)
- [x] Configurable poll intervals (Options Flow, 2026-07-04): sensor
      coordinator and NV coordinator intervals are now user-configurable
      via Settings → Devices & Services → Windhager InfoWIN →
      Configure → Poll intervals. Defaults: 1 min (sensors), 5 min
      (NVs). Note: a single poll takes ~17-20s, so intervals below
      30s are not useful in practice.
- [ ] Optimized/parallel polling — rejected for initial discovery
      crawl (burst of ~80-280 requests, risk to heating controller);
      steady periodic polling is fine since the official web interface
      also polls every 30s.
- [ ] Change detection (skip coordinator write if value unchanged)

---

## Home Assistant

### Config Flow

- [x] Host / Username / Password
- [x] Select discovered modules
- [x] Select sensor groups (per module)
- [x] Connection errors surfaced in form
- [x] Reconfigure options (module/group selection changeable after setup)
- [x] Configurable poll intervals (2026-07-04)

### Sensor

- [x] Basic sensors
- [x] Metadata mapping (units, device classes, state classes)
- [x] Unit translation (Windhager-specific → HA units)
- [x] Readable naming
- [x] Icons, entity categories, device classes, state classes
- [x] Date/time parsing
- [x] Stable readable entity_ids (suggested_object_id)
- [x] Graceful handling of placeholder values ("-")
- [x] PMX combustion state sensor (2026-07-04): NV index 27 translated
      to human-readable labels. Verified 5 days / 17 cycles on BioWIN
      2 Touch. Unknown states fall back to raw hex with known_state=False.
- [x] Last known state on startup (2026-07-06): all sensors show their
      last known value immediately after restart instead of "-" /
      "Unknown" while waiting for the first coordinator refresh.
      WindhagerSensor.live_entry reads from HA state cache as fallback;
      WindhagerPmxStateSensor._raw_hex reads last "raw" attribute.

### Number / Select

- [x] Writable values as NumberEntity / SelectEntity (v0.6.0)
- [x] Instant UI feedback after write (cache patch + background refresh)

### Button

- [x] "Refresh now" button entities (2026-07-04): two ButtonEntity
      instances — one for sensor coordinator, one for NV coordinator.
      Triggers async_request_refresh() for immediate poll.

### Devices

- [x] Basic device per module
- [ ] Better device hierarchy via `via_device` — mark HK1/HK2/HK3 as
      connected through BioWIN. Needs a generic way to identify "the
      boiler" module without hardcoding "BioWIN". Revisit when data
      from other installations is available.

### Branding / Packaging

- [x] Custom icon/logo, dark mode variants
- [x] manifest.json complete (keys alphabetically sorted per hassfest)
- [x] hacs.json (with render_readme: true)
- [x] GitHub Actions: HACS validation + hassfest (2026-07-05)
- [x] Conditional NV first refresh
- [x] Entity category reconciliation on every setup
- [x] English log messages (2026-07-04)

---

## Compatibility

- [x] MES INFINITY + InfoWIN Touch (RC7030, firmware S 1.0.2) — tested
- [ ] MES PLUS (older, non-Touch) — untested, likely compatible
- [ ] Newer firmware / comWinStack API — likely NOT compatible
- [ ] Multiple firmware versions / automatic capability detection
- [x] Missing XML entries handling (graceful fallback)
- [ ] Unknown modules handling — generic discovery code should work,
      but unverified on other installations

---

## Release / Project

- [x] Localization (de/en/fr/it)
- [x] README documentation (English)
- [x] LICENSE (MIT)
- [x] Remove credentials from git history
- [x] First HACS-compatible release (v0.1.1)
- [x] Unit tests (41 tests, 2026-06-30)
- [x] Community forum post (2026-06-29)
- [x] HACS default store PR submitted (2026-07-05) — pending review

---

## Future

- [ ] Refine NV group selection: currently a single "NV's" checkbox
      covers all ~200 NV entries — too coarse. Individual per-NV
      selection isn't practical (most NVs have cryptic raw names).
      Revisit once more NV names are known, or find a sensible grouping
      (e.g. by snvt_name/category).
- [ ] Pellet consumption unit factor: raw NV value appears to be in
      10kg units (10.206 → 102.06t). Workaround: template sensor.
      Consider an optional calibration field in the Options Flow once
      verified on other installations.
- [ ] Better device hierarchy via `via_device` (see Devices above)
- [ ] Firmware capability report
- [ ] Change detection
- [ ] Parallelized/faster initial discovery (rejected for now —
      risk to heating controller not worth the time saved)
