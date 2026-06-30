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
- [x] Unknown type report / Unknown unit report / Unknown subtype
      report - originally vague TODO holdovers, investigated
      2026-06-30. Findings:
        - typeId is NOT a reliable single-value enum marker as
          initially hoped - Windhager uses at least TWO different
          typeId values for enums (0 for small enums like
          "senden/verwenden/lokale TA", 9 for larger ones like
          Betriebswahl), so a small typeId whitelist would have been
          incomplete and fragile with only a handful of observed
          samples.
        - typeId 4 = date/time (distinguished via unitId 20/21,
          matching what entry.unit already does)
        - typeId 13 = numeric value with a unit
        - NV entries (NvEntry) don't have typeId at all - they use a
          completely separate type system via snvtName (SNVT_count,
          SNVT_temp_p, SNVT_obj_status, etc.). snvtIndex=0 with no
          snvtName correlates with the known hex/bitfield values
          (PMX_Status, GB_m, etc.) - the existing is_raw_hex_value()
          text-based check already handles this correctly in
          practice.
      Implemented instead: Entry now carries the API's own "enum"
      field directly (the list of valid values, e.g. [0,1,2,3,4,5]) -
      a far more reliable enum marker than any typeId-based
      whitelist, since it comes straight from the API regardless of
      which numeric typeId happens to be used. See is_enum_value() in
      metadata.py. Decided NOT to pursue a full typeId/snvtName-based
      reclassification of device_class()/has_numeric_value() - the
      enum field covers the one case (enum vs. numeric ambiguity)
      where it would have mattered; the rest of the existing
      unit-string-based logic already works correctly for the
      remaining types observed.
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
- [x] Entity category reconciliation on every setup (added
      2026-06-30): HA only evaluates entity_category on an entity's
      FIRST registration, not on subsequent restarts - found via live
      testing that this isn't just a development quirk, a normal
      HACS update (new files + restart, no manual re-add) hits the
      same pattern, meaning classification fixes would silently not
      apply to already-installed setups. _reconcile_entity_categories()
      now compares each existing entity's stored category against
      what the current code computes and corrects mismatches via the
      registry. Must run AFTER the NV coordinator's refresh completes
      (in both the blocking and background paths) - running it
      earlier was an actual bug caught during testing (live values
      not yet available, so classification was based on the "-"
      catalog placeholder instead of the real value).
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
- [x] Unit tests - 41 tests added 2026-06-30 (test_resources.py,
      test_metadata.py, test_catalog.py, test_system.py), focused on
      the most non-trivial logic and the bugs found during this
      project's development (fcttyp lookup-name collisions, hex value
      diagnostic classification, enum translation, catalog error
      recovery). Runs without a full Home Assistant install via a
      minimal mock in conftest.py.
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
