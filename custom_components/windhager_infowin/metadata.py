from datetime import datetime

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.const import EntityCategory


DIAGNOSTIC_LOOKUPS = {
    "Modulinfo",
}


# NV-Variablen (anhand ihres technischen Rohnamens, OHNE Array-Suffix
# wie "[0]"), die monoton steigende Zaehler sind (Betriebsstunden,
# Anzahl-Zaehler, Verbrauchssummen). Diese bekommen state_class
# TOTAL_INCREASING statt MEASUREMENT, damit HA sie als Zaehler in
# Langzeitstatistiken/im Energie-Dashboard sinnvoll behandelt (siehe
# state_class()).
#
# HINWEIS: nvoError/nviError/FA_nvoError (SNVT_count, aber inhaltlich
# vermutlich eher Fehlercodes/-aufzaehlungen als echte monoton
# steigende Verschleisszaehler) sind hier BEWUSST NICHT gelistet, da
# unklar ist, ob sie tatsaechlich nur hochzaehlen. Im Zweifel lieber
# MEASUREMENT (Standard-Fallback) statt falscher Zaehler-Semantik.
TOTAL_INCREASING_NV_NAMES = {
    "PMX_eeBetrStd",
    "PMX_eeNbrAnhz",
    "FS_ioMsum",
    "RUE_cntError",
    "RUE_cntEntaZue",
}


# Device-Classes, fuer die HA KEINEN state_class erlaubt (ausser
# evtl. TOTAL, was wir hier nicht verwenden) - siehe Home Assistant
# Developer Docs zu SensorStateClass.MEASUREMENT.
_NO_STATE_CLASS_DEVICE_CLASSES = {
    SensorDeviceClass.DATE,
    SensorDeviceClass.ENUM,
    SensorDeviceClass.ENERGY,
    SensorDeviceClass.GAS,
    SensorDeviceClass.MONETARY,
    SensorDeviceClass.TIMESTAMP,
    SensorDeviceClass.VOLUME,
    SensorDeviceClass.WATER,
}


# Windhager liefert teils deutsche/eigene Einheitenkuerzel, die HA
# nicht kennt (z.B. "Std" statt "h"). Diese Tabelle uebersetzt die
# rohe Windhager-Einheit in die von HA erwartete Konstante, BEVOR sie
# als native_unit_of_measurement gesetzt wird. Einheiten, die hier
# nicht aufgefuehrt sind, werden unveraendert durchgereicht.
UNIT_TRANSLATIONS = {
    "Std": "h",
}


def translate_unit(unit):
    """Rohe Windhager-Einheit in eine von HA erkannte Einheit
    uebersetzen (z.B. "Std" -> "h"). Unbekannte/bereits passende
    Einheiten werden unveraendert zurueckgegeben.
    """

    if unit is None:
        return None

    return UNIT_TRANSLATIONS.get(unit, unit)


def parse_date(value):
    """Windhager-Datumsstring ("26.06.2026") in ein Python date-
    Objekt parsen. Liefert None bei ungueltigem/Platzhalter-Wert
    (z.B. "-"), wie von HA fuer device_class DATE gefordert.
    """

    try:

        return datetime.strptime(
            str(value),
            "%d.%m.%Y",
        ).date()

    except (ValueError, TypeError):

        return None


def parse_time(value):
    """Windhager-Zeitstring ("22:04") in ein Python time-Objekt
    parsen. Liefert None bei ungueltigem/Platzhalter-Wert.
    """

    try:

        return datetime.strptime(
            str(value),
            "%H:%M",
        ).time()

    except (ValueError, TypeError):

        return None


# WICHTIG: Keys sind die ROHEN Windhager-Einheiten (vor der
# Uebersetzung durch translate_unit), da device_class() auf
# entry.unit direkt zugreift. "rpm" hat bewusst KEINE device_class,
# da UnitOfFrequency nur mHz/Hz/kHz/MHz/GHz zulaesst und rpm damit
# keine gueltige Kombination waere - der Sensor zeigt den Wert dann
# einfach ohne device_class-spezifische Formatierung/Icon-Override.
#
# "21" (reine Uhrzeit ohne Datum) hat bewusst KEINE device_class:
# SensorDeviceClass.TIME existiert in Home Assistant nicht (nur DATE
# fuer reines Datum und TIMESTAMP fuer volles Datum+Zeit mit
# Zeitzone) - der Wert wird ueber parsed_value() trotzdem als echtes
# datetime.time-Objekt geliefert, einfach ohne device_class-Tag.
DEVICE_CLASSES = {
    "°C": SensorDeviceClass.TEMPERATURE,
    "K": SensorDeviceClass.TEMPERATURE,
    "bar": SensorDeviceClass.PRESSURE,
    "V": SensorDeviceClass.VOLTAGE,
    "A": SensorDeviceClass.CURRENT,
    "Hz": SensorDeviceClass.FREQUENCY,
    "W": SensorDeviceClass.POWER,
    "kW": SensorDeviceClass.POWER,
    "Wh": SensorDeviceClass.ENERGY,
    "kWh": SensorDeviceClass.ENERGY,
    "kg": SensorDeviceClass.WEIGHT,
    "Std": SensorDeviceClass.DURATION,
    "min": SensorDeviceClass.DURATION,
    "d": SensorDeviceClass.DURATION,
    "20": SensorDeviceClass.DATE,
}


def classify(entry, lookup=None):

    if lookup and lookup.name in DIAGNOSTIC_LOOKUPS:
        return "diagnostic"

    unit = entry.unit

    if unit in ("°C", "K"):
        return "temperature"

    if unit == "%":
        return "percentage"

    if unit == "bar":
        return "pressure"

    if unit in ("W", "kW"):
        return "power"

    if unit in ("Wh", "kWh"):
        return "energy"

    if unit == "V":
        return "voltage"

    if unit == "A":
        return "current"

    if unit == "Hz":
        return "frequency"

    if unit == "min":
        return "duration"

    if unit == "Std":
        return "duration"

    if unit == "d":
        return "duration"

    if unit == "kg":
        return "weight"

    if unit == "rpm":
        # rpm hat KEINE gueltige HA-Device-Class (UnitOfFrequency
        # erlaubt nur mHz/Hz/kHz/MHz/GHz, nicht rpm) - eigene
        # Kategorie nur fuer Icon-Zwecke, ohne device_class().
        return "rotation_speed"

    if unit == "20":
        return "date"

    if unit == "21":
        return "time"

    # NvEntry hat kein write_protected-Attribut (NV's sind grundsaetzlich
    # nur lesbare Mess-/Statuswerte, daher "sensor" als Default).
    if getattr(entry, "write_protected", True):
        return "sensor"

    return "setting"


def device_class(entry):

    return DEVICE_CLASSES.get(entry.unit)


def state_class(entry, live_value=None):
    """SensorStateClass fuer Langzeitstatistiken/Graphen bestimmen.

    - Monoton steigende Zaehler (Betriebsstunden, Anheizvorgaenge,
      Foerdermengen-Summe, Fehlerzaehler) -> TOTAL_INCREASING.
    - Echte Momentanmesswerte (Temperatur, Drehzahl, Prozent, Druck,
      Lagerbestand etc.) -> MEASUREMENT.
    - Nicht-numerische oder reine Status-/Text-Werte (z.B. "Status",
      "Zustand", Datum/Zeit) -> kein state_class (None), da HA dies
      fuer einige device_classes (DATE, ENUM, ...) ohnehin verbietet
      und es bei reinen Statuswerten auch inhaltlich keinen Sinn hat.
    """

    if not has_numeric_value(entry, live_value):
        return None

    dclass = device_class(entry)

    if dclass in _NO_STATE_CLASS_DEVICE_CLASSES:
        return None

    # NvEntry-Name (ohne Array-Suffix wie "[0]") gegen die Zaehler-
    # Whitelist pruefen. entry.name existiert bei normalen OID-
    # Entries ebenfalls, hat dort aber nie einen der gelisteten Werte.
    base_name = (entry.name or "").split("[")[0]

    if base_name in TOTAL_INCREASING_NV_NAMES:
        return SensorStateClass.TOTAL_INCREASING

    return SensorStateClass.MEASUREMENT


def entity_category(lookup):

    if lookup.name in DIAGNOSTIC_LOOKUPS:
        return EntityCategory.DIAGNOSTIC

    return None


def suggested_precision(entry):

    if entry.unit == "°C":
        return 1

    if entry.unit == "%":
        return 0

    return None


def has_numeric_value(entry, live_value=None):
    """Pruefen, ob der aktuelle Wert tatsaechlich eine Zahl ist.

    Bewusst NICHT mehr anhand von entry.unit vorgefiltert: viele
    NV-Variablen (z.B. SNVT_count-Zaehler wie FS_ioMsum, nvoError)
    haben keine Einheit, sind aber trotzdem echte numerische Werte.
    Reine Status-/Modus-Codes (SNVT_obj_status, SNVT_hvac_mode etc.)
    liefern dagegen ohnehin keinen reinen Zahlenwert oder ihr
    Platzhalter "-" wird hier ebenfalls korrekt als nicht-numerisch
    erkannt.

    Datum/Zeit-Werte gelten hier bewusst NICHT als "numerisch" (siehe
    has_valid_value()/parsed_value() fuer diese) - state_class macht
    fuer Datum/Zeit ohnehin keinen Sinn (HA verbietet state_class fuer
    device_class DATE explizit).
    """

    value = entry.value if live_value is None else live_value

    try:

        float(
            str(value).replace(",", ".")
        )

        return True

    except (ValueError, TypeError):

        # z.B. NV-Werte, die noch nicht gepollt wurden ("-"),
        # oder nicht-numerische Statuswerte.
        return False


def has_valid_value(entry, live_value=None):
    """Pruefen, ob der aktuelle Wert ueberhaupt sinnvoll dargestellt
    werden kann - entweder als Zahl ODER als gueltiges Datum/Zeit.

    Wird von sensor.py verwendet, um zu entscheiden, ob device_class/
    unit_of_measurement/precision ueberhaupt gesetzt werden duerfen
    (sonst denkt HA z.B. bei device_class=date "das ist ein Datum",
    obwohl der Wert noch der Platzhalter "-" ist, und stuerzt ab).
    """

    if has_numeric_value(entry, live_value):
        return True

    value = entry.value if live_value is None else live_value

    if entry.unit == "20":
        return parse_date(value) is not None

    if entry.unit == "21":
        return parse_time(value) is not None

    return False


def parsed_value(entry, live_value=None):
    """Den aktuellen Wert in das von HA fuer die jeweilige
    device_class erwartete Python-Objekt umwandeln:

    - device_class DATE  -> datetime.date
    - device_class TIME  -> datetime.time
    - alles andere       -> Rohwert unveraendert (Zahl bleibt String,
      HA/SensorEntity wandelt das selbst passend um)
    """

    value = entry.value if live_value is None else live_value

    if entry.unit == "20":
        return parse_date(value)

    if entry.unit == "21":
        return parse_time(value)

    return value


def icon(entry, lookup=None):

    kind = classify(entry, lookup)

    icons = {
        "temperature": "mdi:thermometer",
        "pressure": "mdi:gauge",
        "power": "mdi:flash",
        "energy": "mdi:lightning-bolt",
        "voltage": "mdi:sine-wave",
        "current": "mdi:current-ac",
        "frequency": "mdi:pulse",
        "rotation_speed": "mdi:fan",
        "duration": "mdi:timer-outline",
        "date": "mdi:calendar",
        "time": "mdi:clock-outline",
        "percentage": "mdi:percent",
        "weight": "mdi:weight-kilogram",
        "diagnostic": "mdi:information-outline",
        "setting": "mdi:cog-outline",
        "sensor": "mdi:chart-line",
    }

    return icons.get(kind)


def metadata(entry, lookup=None, live_value=None):

    return {
        "classification": classify(entry, lookup),
        "device_class": device_class(entry),
        "state_class": state_class(entry, live_value),
        "entity_category": entity_category(lookup) if lookup else None,
        "precision": suggested_precision(entry),
        "icon": icon(entry, lookup),
        "numeric": has_numeric_value(entry, live_value),
        "valid": has_valid_value(entry, live_value),
        "value": parsed_value(entry, live_value),
    }