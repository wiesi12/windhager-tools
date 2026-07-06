"""NV-Gruppen-Mapping fuer die snvt-basierte Feinauswahl.

Teilt NV-Eintraege anhand ihres snvt_name in universelle Gruppen auf.
Die Gruppen basieren bewusst NICHT auf NV-Namen (die anlagenspezifisch
sind), sondern ausschliesslich auf dem standardisierten LON-Typ
snvt_name - damit funktioniert die Gruppenauswahl auf jeder Anlage,
auch wenn die NV-Namen unbekannt sind.

Verifiziert auf: BioWIN 2 Touch (PMX-Controller), MES INFINITY.
Distribution: Temperaturen 80x, Betrieb/Status 56x,
Leistung/Drehzahlen 33x, Zaehler/Laufzeiten 27x, Sonstige 5x.
"""

# snvt_name -> (group_key, group_label_de)
# None = kein snvt_name gesetzt (hex/bitfield-Werte wie PMX_Status,
# GB_m etc.) -> Betrieb & Status
SNVT_GROUP_MAP: dict[str | None, tuple[str, str]] = {
    # Temperaturen
    "SNVT_temp_p": ("nv_group_temperatures", "Temperaturen"),
    "SNVT_temp":   ("nv_group_temperatures", "Temperaturen"),
    # Leistung, Drehzahlen, Fuellstand, Masse
    "SNVT_rpm":         ("nv_group_power", "Leistung & Drehzahlen"),
    "SNVT_lev_cont":    ("nv_group_power", "Leistung & Drehzahlen"),
    "SNVT_lev_percent": ("nv_group_power", "Leistung & Drehzahlen"),
    "SNVT_mass_kilo":   ("nv_group_power", "Leistung & Drehzahlen"),
    # Zaehler, Laufzeiten, Zeitstempel
    "SNVT_count":      ("nv_group_counters", "Zähler & Laufzeiten"),
    "SNVT_time_hour":  ("nv_group_counters", "Zähler & Laufzeiten"),
    "SNVT_time_min":   ("nv_group_counters", "Zähler & Laufzeiten"),
    "SNVT_time_stamp": ("nv_group_counters", "Zähler & Laufzeiten"),
    # Betrieb, Status, Modi, hex/bitfield (snvt_name == None)
    "SNVT_hvac_mode":   ("nv_group_status", "Betrieb & Status"),
    "SNVT_obj_status":  ("nv_group_status", "Betrieb & Status"),
    "SNVT_state":       ("nv_group_status", "Betrieb & Status"),
    "SNVT_obj_request": ("nv_group_status", "Betrieb & Status"),
    None:               ("nv_group_status", "Betrieb & Status"),
}

# Fallback fuer alle nicht explizit gemappten snvt_names
NV_GROUP_OTHER = ("nv_group_other", "Sonstige")

# Alle bekannten Gruppen in der gewuenschten Anzeigereihenfolge
NV_GROUP_ORDER = [
    "nv_group_temperatures",
    "nv_group_power",
    "nv_group_counters",
    "nv_group_status",
    "nv_group_other",
]

NV_GROUP_LABELS = {
    "nv_group_temperatures": "Temperaturen",
    "nv_group_power":        "Leistung & Drehzahlen",
    "nv_group_counters":     "Zähler & Laufzeiten",
    "nv_group_status":       "Betrieb & Status",
    "nv_group_other":        "Sonstige",
}


def snvt_to_group(snvt_name: str | None) -> str:
    """snvt_name -> group_key."""
    return SNVT_GROUP_MAP.get(snvt_name, NV_GROUP_OTHER)[0]


def groups_for_module(module) -> list[tuple[str, str]]:
    """Liste (group_key, label) der NV-Gruppen die in diesem Modul
    tatsaechlich vorkommen, in der definierten Reihenfolge.

    Gibt eine leere Liste zurueck wenn das Modul keine NV-Eintraege hat.
    """

    from .models import NvEntry

    present = set()

    for function in module.functions:
        for lookup in function.lookups:
            for entry in lookup.entries:
                if isinstance(entry, NvEntry):
                    present.add(snvt_to_group(entry.snvt_name))

    return [
        (key, NV_GROUP_LABELS[key])
        for key in NV_GROUP_ORDER
        if key in present
    ]


def filter_nv_entries(entries, selected_groups: list[str]):
    """NV-Entries auf die gewaehlten Gruppen filtern.

    Nicht-NV-Entries (OID-Entries) werden immer durchgereicht.
    Wenn selected_groups leer ist oder None, werden alle NV-Entries
    behalten (Rueckwaertskompatibilitaet).
    """

    from .models import NvEntry

    if not selected_groups:
        return entries

    return [
        entry for entry in entries
        if not isinstance(entry, NvEntry)
        or snvt_to_group(entry.snvt_name) in selected_groups
    ]
