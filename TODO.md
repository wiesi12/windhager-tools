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
- [x] Change detection (2026-07-06): Poller now caches the last known
      value per key and only triggers a coordinator update when a value
      actually changes — reduces unnecessary HA state writes during
      standby (e.g. when the boiler hasn't changed state between polls).
- [ ] Optimized/parallel polling — rejected for initial discovery
      crawl (burst of ~80-280 requests, risk to heating controller);
      steady periodic polling is fine since the official web interface
      also polls every 30s.

---

## Home Assistant

### Config Flow

- [x] Host / Username / Password
- [x] Select discovered modules
- [x] Select sensor groups (per module)
- [x] Connection errors surfaced in form
- [x] Reconfigure options (module/group selection changeable after setup)
- [x] Configurable poll intervals (2026-07-04)
- [x] NV sensor group selection (2026-07-06): snvt-based grouping
      (Temperaturen, Leistung & Drehzahlen, Zähler & Laufzeiten,
      Betrieb & Status, Sonstige) — universal across all installations.
      Available in Options Flow after first setup. Implemented in
      nv_groups.py; filtered in system.py per selected_nv_groups.
- [x] Sensor calibration step (2026-07-06): pellet consumption unit
      factor configurable via Options Flow. Default 1.0 (no conversion).
      On BioWIN 2 Touch: factor 10 → result in tonnes.

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
- [x] Pellet consumption sensor (2026-07-06): WindhagerPelletSensor
      for NV index 19 with configurable unit factor. Only created when
      nv:60:19 exists in oid_map (BioWIN-specific, not hardcoded).

### Number / Select

- [x] Writable values as NumberEntity / SelectEntity (v0.6.0)
- [x] Instant UI feedback after write (cache patch + background refresh)

### Schedule (Zeitprogramme)

- [x] Generic discovery (2026-07-28): time programs (typeId 30) live
      in an address space the normal lookup-group listing can't
      enumerate (409 Conflict). Discovery reads the device's own
      `res/xml/StaticNav.xml` resource for the authoritative list of
      time-program positions (group/member + real translated name),
      then checks every function of every module against that list
      (lib/schedules.py) - no hardcoded group/module list, no member
      range guessing, self-updating if the firmware adds more.
- [x] Read via dedicated `object` endpoint (`get_object`/
      `write_object` in lib/client.py) - the normal `lookup`/
      `datapoint` endpoints never return the actual switchPoints
      value for this object type.
- [x] Multi-block support (2026-07-28): a time program can have
      multiple switch-point groups with different weekdays (e.g. a
      DHW program with different values for Mon-Sat vs. Sunday,
      verified via browser devtools) - `write_schedule()`/
      `set_schedule` service take a `blocks` list, not a single
      switch-points/weekdays pair.
- [x] `WindhagerScheduleCoordinator` (5 min default) + sensor with
      the full block list (switchPoints/weekdays) as attribute.
- [x] `windhager_infowin.set_schedule` service for writing.
- [ ] Verified only on a single installation (3 heating circuits +
      1 DHW time program found so far) - the StaticNav.xml-based
      discovery itself is generic, but real-world variety (more/fewer
      circuits, other program types) is untested.

### Frontend

- [x] Custom Lovelace card for viewing/editing a time program (switch
      points + weekdays across multiple blocks) instead of raw sensor
      attributes / Developer Tools YAML, single entity or multiple
      with a dropdown to switch. Moved into its own repository
      (2026-07-28) for separate HACS (Dashboard/plugin) distribution:
      [windhager-schedule-card](https://github.com/wiesi12/windhager-schedule-card).
      Verified with a static mocked-`hass` test harness AND live on a
      real Home Assistant dashboard, incl. writing a DHW time program.

### Button

- [x] "Refresh now" button entities (2026-07-04): two ButtonEntity
      instances — one for sensor coordinator, one for NV coordinator.
      Triggers async_request_refresh() for immediate poll.

### Devices

- [x] Basic device per module
- [x] Device hierarchy via `via_device` (2026-07-28): rather than
      guessing which module is "the boiler" (unreliable — e.g. BioWIN
      has no distinguishing function type of its own, all its data
      comes through NV variables), the user explicitly picks the
      heat generator module in the Options Flow
      (`config_flow.py::async_step_select_boiler`). Default "none"
      keeps the previous flat structure. Verified live: HK1/HK3
      devices now report `via_device_id` pointing at BioWIN.

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

- [ ] Firmware capability report
- [ ] Parallelized/faster initial discovery (rejected for now —
      risk to heating controller not worth the time saved)
