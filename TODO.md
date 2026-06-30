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
- [x] Typed value helpers (covered pragmatically via
      metadata.parsed_value()/has_numeric_value()/has_valid_value() in
      the HA integration layer rather than as methods on Entry itself)
- [x] Enum helper methods - implemented 2026-06-30. Windhager exposes
      a fourth resource file alongside EbenenTexte/VarIdentTexte at
      /res/xml/AufzaehlTexte_<lang>.xml, addressed by (group, member,
      enum_value) - one level more specific than VarIdentTexte's
      (group, member). Loaded in resources.py, stored as part of the
      catalog (format changed to {modules, enum_texts}, old catalogs
      without enum_texts still load fine). metadata.parsed_value()
      returns the readable text instead of the raw value when a
      translation exists, and has_numeric_value()/state_class()
      correctly treat such values as non-numeric (a status code isn't
      a measurement). Verified live: HK1 Betriebswahl shows "Standby",
      HK2 shows "Heizprogramm 1" - different, genuinely current
      per-circuit values, not a coincidence.

### Catalog

- [x] Save catalog
- [x] Load catalog
- [x] Per-language catalog caching
- [x] Store catalog inside the integration directory (persistent_directory)
- [x] Catalog versioning / schema migration - solved pragmatically
      2026-06-29: rather than a full migration system, load_catalog()
      failures (corrupt JSON, missing fields after a data model
      change) are now caught, the stale catalog file is deleted, and
      a fresh discovery crawl runs automatically - same recovery path
      as a missing catalog, just triggered by a broken one too.

### Diagnostics

- [x] Statistics
- [x] Validation
- [ ] Unknown type report / Unknown unit report / Unknown subtype
      report - originally vague TODO holdovers, but turned out to
      point at something real: the lookup API returns numeric
      `typeId`/`unitId`/`subtypeId` fields per entry that we already
      read and store (Entry.type_id/unit_id/subtype_id) but never
      actually use anywhere. Confirmed via live API responses
      2026-06-30:
        - typeId 9 = enum value (response also includes an `enum`
          field, e.g. "[0,1,2,3,4,5]", listing the valid raw values -
          and notably, NO `unit` field in this case)
        - typeId 13 = numeric value with a unit (response includes
          `unit`/`unitId`/`minValue`/`maxValue`/`step`, e.g.
          unitId 1 = "°C" - and no `enum` field)
      typeId looks like a much more reliable way to distinguish
      "this is an enum" vs. "this is a plain number" than our current
      approach (guessing from entry.unit being a known string or
      None). Could also replace/supplement the hardcoded
      DEVICE_CLASSES unit-string mapping in metadata.py with a
      unitId-based one, which wouldn't depend on Windhager's unit
      text staying consistent. Worth a closer look, but a real
      refactor (touches classify()/device_class()/has_numeric_value()
      and the catalog schema), not a quick change - and ties in
      directly with the enum-helper-methods idea above (typeId == 9
      would be the trigger for looking up the AufzaehlTexte mapping).
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
      selection after initial setup). Idea from 2026-06-29: show the
      CURRENT/live sensor value next to each module/group checkbox
      when reconfiguring (not during initial setup) - the coordinator
      is already running with real data at that point, so this is
      free (no extra API calls), unlike trying to preview values
      during the initial config flow, which would need a full extra
      polling round-trip before the user can even see the checkboxes
      (considered and rejected for the initial setup specifically -
      doubles the wait time for not much benefit, since the user
      hasn't seen anything yet anyway at that point).

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

- [ ] Add `number`/`select` entity platforms for writable values (see
      "Write support" under Future for the confirmed API details -
      write endpoint, payload format, and the typeId-based
      enum/numeric distinction found while investigating this).
      Originally four separate bullet points here (read/write values,
      min/max/step, lookup enums, write support) - consolidated since
      they're really one feature and the details belong in one place
      instead of being duplicated.

### Devices

- [x] Basic device per module
- [ ] Better device hierarchy - precise idea 2026-06-30 (after
      rejecting function-level devices above): use HA's `via_device`
      in DeviceInfo to mark HK1/HK2/HK3 as connected through BioWIN
      (the actual boiler the heating circuits draw heat from). Purely
      visual/navigational in the HA device list (shows "via [device]"
      linkage) - doesn't create any new entities or devices, so none
      of the downsides of function-level devices apply. Would need to
      figure out which module is "the boiler" generically (not
      hardcoded to "BioWIN" specifically, since other installations
      will have different module names) - maybe by module type/fctType
      pattern rather than name matching.

      Investigated 2026-06-30 without finding a clean answer:
        - lookup/1 (top-level module discovery) includes a
          `device: {id: N}` field per module - HK1/HK2/HK3 all share
          the same device.id (9), while BioWIN has a different one
          (1), and the "n.a." module has no device field at all. This
          shows HK1-3 share one physical hardware node, but doesn't
          identify "the boiler" - it's a different (also potentially
          useful) grouping than what this TODO item is about.
        - Checked /res/xml/StaticNav.xml, MapToInstance.xml, and
          StaticNavAssignment.xml (previously unexplored resource
          files) hoping one would explicitly describe module
          relationships. None of them do - StaticNav.xml covers
          UI elements like time programs/error logs/password fields
          (and reveals 2 more languages, es/nl, beyond the 4 currently
          supported); MapToInstance.xml documents known multi-instance
          module types (fctType 4 = "Kaskadenmanager", 12 = "IO5500",
          13 = "Solar ES" - more module types than this integration
          has ever seen); StaticNavAssignment.xml maps functiontype
          values to which StaticNav UI elements they get. None of
          these address "which module is the boiler".
      Remains unsolved with only one test installation - revisit if/
      when there's data from an installation with a different module
      structure to compare against.
- [x] ~~Function-level devices~~ - considered and rejected 2026-06-30:
      would mean one HA device per lookup group (e.g. separate
      devices for "Betriebswahl", "Auslegungstemperaturen", etc.
      instead of one device per module). For HK1-3 (which have ~20
      lookup groups each) this would balloon the device list from 4
      devices to 60-80+, hurting overview rather than helping it.
      The one module that's actually a single giant group (BioWIN,
      just "NV's" with ~200 entries) wouldn't even benefit, since
      there's nothing to split there. Current per-module device with
      group-prefixed sensor names (e.g. "HK1 OG1/2 Betriebswahl ...")
      already gives the grouping without the device list explosion.

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
- [x] Missing XML entries handling - already covered: lookup_name()/
      entry_name() in resources.py both fall back to an empty string
      rather than raising, so missing translations don't crash
      discovery (just show a blank/raw name instead). Was implicit
      in how the naming pipeline was built rather than a deliberate
      separate effort, but the behavior is there.
- [ ] Unknown modules handling - discovery code itself is fully
      generic (parses whatever the API returns, no module-type-
      specific assumptions), so it should handle module types this
      integration has never seen (solar, heat pump, etc.) without
      changes - but this has only ever run against this integration's
      one test installation, so it's unverified in practice.

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
      Writable lookup responses also already include `minValue`,
      `maxValue`, `step`/`stepId`, and `writeProt` (confirmed
      2026-06-30 via live lookup responses for room temperature
      setpoints - e.g. minValue "10.0", maxValue "30.0", step "0.5")
      - everything needed to build proper `number` entities with
      correct bounds, without having to guess or hardcode them. See
      the typeId entry above for how to tell enum vs. numeric values
      apart (`select` vs. `number` entities).
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
