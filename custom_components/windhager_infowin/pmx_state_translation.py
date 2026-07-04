# PMX State Translation for Windhager BioWIN
#
# State format: 0xHHLL
#   HH = main phase (high byte)
#   LL = sub-variant (low byte)
#
# VERIFICATION STATUS:
#   Main phases (HH): HIGH confidence — derived from 5 days / 17 complete
#     combustion cycles on a BioWIN 2 Touch (PMX controller), cross-correlated
#     with blower speed, ignition temp, pellet demand, and setpoint sensors.
#     Core combustion physics are unlikely to differ across BioWIN models.
#
#   Sub-variants (LL): MEDIUM confidence — verified on ONE unit only.
#     Specific sub-variants (e.g. 0x0302, 0x0611) may differ by:
#       - firmware version
#       - boiler power class (35/50/70/... kW)
#       - installed options (e.g. modulation capability for 0x0502)
#     If you see unknown LL values on your unit, please open an issue and
#     share your InfluxDB/Chronograf export — it helps expand this map.
#
# FALLBACK BEHAVIOUR:
#   Unknown states are NOT treated as errors. The sensor returns the raw
#   hex value with known_state=False so data collection continues uninterrupted.
#   This is intentional: users on different firmware/models can still gather
#   data and contribute to extending this map.
#
# Last updated: 2026-07-04
# Verified on:  Windhager BioWIN 2 Touch, PMX controller
# Data source:  5 days, 17 cycles, 12-second polling via WindhagerDebugCoordinator

# ---------------------------------------------------------------------------
# MAIN PHASE MAP  (HH byte only, 0xHH00 mask)
# High confidence — applicable to all BioWIN PMX units.
# ---------------------------------------------------------------------------
PMX_MAIN_PHASE: dict[int, str] = {
    0x01: "Standby",
    0x02: "Zündvorbereitung",
    0x03: "Zündung",
    0x04: "Hochbrennen",
    0x05: "Volllast",
    0x06: "Bereitschaft",
}

# ---------------------------------------------------------------------------
# FULL STATE MAP  (0xHHLL exact match)
# Medium confidence — verified on one unit, firmware unknown.
# Sub-variants within the same main phase share the same physical meaning
# but differ in detail (e.g. pellet burst vs flame confirmation).
# ---------------------------------------------------------------------------
PMX_STATE_MAP: dict[int, dict] = {
    # --- 0x01xx  Standby / Aus ---
    # Blower off, pellet demand 0, no setpoints active.
    # Long stays (hours) between combustion cycles are normal.
    0x0100: {
        "label": "Standby",
        "phase": "Standby",
        "active": False,
        "confidence": "high",
    },

    # --- 0x02xx  Zündvorbereitung ---
    # Blower deliberately throttled to 0 rpm, ignition temp still ambient.
    # Very short phase (~36 s median, 24–37 s range) — fixed prep step.
    0x0200: {
        "label": "Zündvorbereitung",
        "phase": "Zündvorbereitung",
        "active": True,
        "confidence": "high",
    },

    # --- 0x03xx  Zündung ---
    # 0x0300: Initial pellet burst (4.7 kg/h demand), blower at low speed.
    # 0x0301: Flame formation — pellet demand drops to 0, blower holds steady,
    #         ignition temp rising. ~60 s, very consistent (49–72 s range).
    # 0x0302: Flame confirmation checkpoint — ALWAYS exactly 12 seconds.
    #         Acts as a branch point:
    #           → 0x0400 if heat demand (setpoints) are active
    #           → 0x0601 if no heat demand (early-morning dry-run pattern)
    #         The 12 s fixed duration strongly suggests a hardware timer.
    0x0300: {
        "label": "Zündung – Pelletstoß",
        "phase": "Zündung",
        "active": True,
        "confidence": "high",
    },
    0x0301: {
        "label": "Zündung – Flammenbildung",
        "phase": "Zündung",
        "active": True,
        "confidence": "medium",  # sub-variant, single unit
    },
    0x0302: {
        "label": "Zündung – Flammenbestätigung",
        "phase": "Zündung",
        "active": True,
        "confidence": "medium",  # 12 s timer, branch point; single unit
    },

    # --- 0x04xx  Hochbrennen / Ramp ---
    # Blower jumps to max (~2200 rpm), ignition temp rising steeply.
    # Pellet demand active (1.5 kg/h). Duration ~3 min median.
    # Only reached after a successful 0x0302 with active heat demand.
    0x0400: {
        "label": "Hochbrennen",
        "phase": "Hochbrennen",
        "active": True,
        "confidence": "high",
    },

    # --- 0x05xx  Volllast / Modulation ---
    # 0x0501: Fixed full load (100%). nvilstg/nvolstg both read 100 —
    #         do NOT use these for actual power tracking in this sub-state.
    # 0x0502: True modulation. Only sub-state where nvilstg (setpoint) and
    #         nvolstg (actual) carry real intermediate values (e.g. 65/70%).
    #         Appears only when heat demand persists long enough — ~2 of 17
    #         cycles in summer operation. More common in heating season.
    0x0501: {
        "label": "Volllast",
        "phase": "Volllast",
        "active": True,
        "confidence": "high",
    },
    0x0502: {
        "label": "Modulation",
        "phase": "Volllast",
        "active": True,
        "confidence": "medium",  # rare in summer; nvilstg/nvolstg valid here
    },

    # --- 0x06xx  Bereitschaft / Nachlauf ---
    # Blower still running, no pellet feed, no active flame.
    # Appears both AFTER a combustion cycle (cool-down) and as the landing
    # state after an aborted ignition (0x0302 → 0x0601, no heat demand).
    #
    # 0x0600: Blower spin-down, ~2 min. Transitions to 0x0100 (Standby).
    #         Sometimes skipped — direct 0x0601 → 0x0200 fast-restart seen.
    # 0x0601: Main nachlauf state, ~12 min median. Blower at ~1500 rpm.
    # 0x0611: Short sub-state, ALWAYS exactly 60–62 s (another fixed timer).
    #         Seen between 0x0502 and 0x0601 — likely an "ausbrand" (burn-out)
    #         confirmation step. Not seen after 0x0501-only cycles.
    0x0600: {
        "label": "Gebläse Auslauf",
        "phase": "Bereitschaft",
        "active": False,
        "confidence": "medium",
    },
    0x0601: {
        "label": "Bereitschaft / Nachlauf",
        "phase": "Bereitschaft",
        "active": False,
        "confidence": "high",
    },
    0x0611: {
        "label": "Bereitschaft – Ausbrand",
        "phase": "Bereitschaft",
        "active": False,
        "confidence": "medium",  # 60 s timer, seen only after 0x0502
    },
}


def translate_pmx_state(raw_hex: int) -> dict:
    """
    Translate a raw PMX state integer into a human-readable dict.

    Returns a dict with:
        label       - human-readable state name (German, matches Windhager UI)
        phase       - main phase name (coarser grouping, good for dashboards)
        active      - True if combustion is actively ongoing
        confidence  - 'high' | 'medium' — how well-verified this state is
        known_state - True if this exact state is in the map
        raw         - original hex string, always included for debugging

    Unknown states are returned with known_state=False and a best-effort
    main_phase lookup so the integration never raises on unseen values.
    """
    raw_str = f"0x{raw_hex:04X}"

    if raw_hex in PMX_STATE_MAP:
        result = dict(PMX_STATE_MAP[raw_hex])
        result["known_state"] = True
        result["raw"] = raw_str
        return result

    # Unknown full state — try main phase fallback
    main_phase_byte = (raw_hex >> 8) & 0xFF
    phase_label = PMX_MAIN_PHASE.get(main_phase_byte, "Unbekannt")

    return {
        "label": raw_str,          # show raw so users can report it
        "phase": phase_label,
        "active": main_phase_byte in (0x02, 0x03, 0x04, 0x05),
        "confidence": "unknown",
        "known_state": False,
        "raw": raw_str,
    }


# ---------------------------------------------------------------------------
# Duration statistics for reference / documentation
# Source: 5 days (2026-06-29 – 2026-07-04), BioWIN 2 Touch, summer operation
# ---------------------------------------------------------------------------
PMX_STATE_DURATION_STATS: dict[int, dict] = {
    0x0100: {"n": 12, "median_s": 22248, "min_s": 12,  "max_s": 31979},
    0x0200: {"n": 17, "median_s": 36,    "min_s": 24,  "max_s": 37},
    0x0300: {"n": 17, "median_s": 512,   "min_s": 354, "max_s": 619},
    0x0301: {"n": 17, "median_s": 60,    "min_s": 49,  "max_s": 72},
    0x0302: {"n": 6,  "median_s": 12,    "min_s": 12,  "max_s": 12},
    0x0400: {"n": 12, "median_s": 194,   "min_s": 13,  "max_s": 208},
    0x0501: {"n": 9,  "median_s": 919,   "min_s": 701, "max_s": 1213},
    0x0502: {"n": 2,  "median_s": 147,   "min_s": 49,  "max_s": 245},
    0x0600: {"n": 17, "median_s": 120,   "min_s": 109, "max_s": 125},
    0x0601: {"n": 17, "median_s": 725,   "min_s": 711, "max_s": 780},
    0x0611: {"n": 9,  "median_s": 60,    "min_s": 60,  "max_s": 62},
}
