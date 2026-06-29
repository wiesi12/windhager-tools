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
- [ ] Optimized/parallel polling (note: the official Windhager web
      interface itself polls every 30 seconds, observed via browser
      dev tools on 2026-06-29, so the device is clearly designed to
      handle frequent polling - our current 5/10 minute intervals are
      conservative by comparison. Still rejected parallelizing the
      *initial* discovery crawl specifically, since that's a burst of
      ~80-280 near-simultaneous requests rather than steady periodic
      polling, which is a different kind of load)
- [ ] Change detection

---

## Home Assistant

### Config Flow

- [x] Host
- [x] Username
- [x] Password (masked input)
- [x] Select discovered modules
- [x] Select sensor groups (per module, after module selection)
- [x] Connection errors surfaced directly in the form
- [ ] Reconfigure options (e.g. poll intervals, changing module/group
      selection after initial setup)

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
- [x] Conditional NV first refresh (blocking only on the very first
      setup, so entity_category is evaluated correctly; background
      task on every subsequent restart for faster startup)
- [x] config_entry passed to coordinators
- [x] Eliminated build_integration.py / vendor/ copy step (lib/ moved
      directly into the integration with relative imports)

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
- [x] README documentation (English)
- [x] LICENSE (MIT)
- [x] Remove credentials from git history
- [x] First HACS-compatible release (v0.1.1, after v0.1.0 turned out
      to predate the HACS-compliance fixes)
- [x] Module/sensor-group selection feature released (v0.2.0)
- [ ] Unit tests
- [ ] Submit to HACS default store (after some real-world testing)
- [x] Community forum post to find testers for other firmware/hardware
      generations (posted 2026-06-29 in Custom Integrations category,
      pending moderator approval as a new account)

## Future

- [ ] Write support (temperature setpoints, modes). Endpoint
      confirmed via browser dev tools while testing the official web
      interface: `PUT /api/1.0/datapoint` with JSON body
      `{"OID": "/1/17/0/3/50/0", "value": "1"}` (OID format matches
      the existing lookup path scheme, just as one string with a
      leading slash instead of separate URL segments). Confirmed
      working with a plain ENDUSER-level login (the same `USER`
      account this integration already uses for reading) - no need
      for SERVICE/OEM credentials. The `ws.setDP.req.xml`/
      `ws.writeDP.req.xml` resources under `/res/xml/` are SOAP and
      NOT what the current web interface actually uses - ignore them,
      they're apparently a leftover from an older API generation.
- [ ] Parallelized/faster initial discovery (carefully, to avoid overloading the webserver) - considered and rejected for now (2026-06-29), risk to the heating controller not worth the time saved on a one-time setup step
- [ ] Refine NV group selection: currently a single "NV's" checkbox
      covers all ~200 NV entries per module (e.g. BioWIN) - too coarse
      for meaningful filtering. Individual per-NV selection isn't
      practical either since most NVs only have a cryptic raw name
      (no entry in nv_names.py). Revisit once more NV names are
      known/whitelisted, or find another sensible grouping
      (e.g. by snvt_name/category).
- [x] Architecture simplification: moved windhager_tools/ directly into
      custom_components/windhager_infowin/lib/ with relative imports
      from the start, eliminating tools/build_integration.py and the
      vendor/ copy step entirely (done 2026-06-29, after the v0.2.0
      release). Also removed pyproject.toml/MANIFEST.in (only existed
      for windhager_tools as a standalone pip package, which is no
      longer a goal) and a stray duplicate manifest.json that had
      ended up at the repo root.
