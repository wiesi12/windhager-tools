"""Tests fuer metadata.py.

Schwerpunkt: die Faelle, die in dieser Session als echte Bugs
gefunden und gefixt wurden -
- rohe Hex-Bitfeld-Werte (z.B. PMX_Status), die als Diagnose-Entity
  markiert werden sollen statt in der normalen Sensorliste zu landen
- Enum-Wert-Uebersetzung (z.B. "0" -> "Standby")
- die Abgrenzung zwischen "numerischer Messwert" und "alles andere"
  (Platzhalter, Hex, Enum, Datum/Zeit)

conftest.py registriert vor dem Import dieses Moduls einen minimalen
homeassistant-Mock, damit diese Tests OHNE installiertes Home
Assistant laufen.
"""

import metadata


class FakeEntry:
    """Minimaler Stand-in fuer windhager_tools.models.Entry/NvEntry -
    nur die Attribute, die metadata.py tatsaechlich anschaut.
    """

    def __init__(
        self,
        value,
        unit=None,
        group=None,
        member=None,
        name="",
        enum=None,
    ):

        self.value = value
        self.unit = unit
        self.group = group
        self.member = member
        self.name = name
        self.enum = enum


class FakeLookup:

    def __init__(self, name):
        self.name = name


def test_is_raw_hex_value_detects_hex_string():

    entry = FakeEntry(
        value=(
            "0x0200010002d61d5a7fff003c1194"
            "00000000000000000000000000000000"
        )
    )

    assert metadata.is_raw_hex_value(entry) is True


def test_is_raw_hex_value_false_for_normal_number():

    entry = FakeEntry(value="65.3")

    assert metadata.is_raw_hex_value(entry) is False


def test_is_raw_hex_value_false_for_placeholder():

    entry = FakeEntry(value="-")

    assert metadata.is_raw_hex_value(entry) is False


def test_entity_category_diagnostic_for_hex_value():
    """Regressionstest fuer den Hex-Bitfeld-Diagnostic-Fix: rohe
    Hex-Werte (z.B. PMX_Status) sollen als Diagnose-Entity markiert
    werden, unabhaengig vom Lookup-Namen.
    """

    lookup = FakeLookup(name="NV's")
    entry = FakeEntry(
        value="0x0100",
    )

    assert (
        metadata.entity_category(
            lookup,
            entry,
            entry.value,
        )
        == "diagnostic"
    )


def test_entity_category_none_for_normal_value():

    lookup = FakeLookup(name="Betriebswahl")
    entry = FakeEntry(value="65.3")

    assert (
        metadata.entity_category(
            lookup,
            entry,
            entry.value,
        )
        is None
    )


def test_entity_category_diagnostic_for_modulinfo_lookup():
    """Modulinfo-Lookup-Gruppen sind grundsaetzlich Diagnose, auch
    bei einem ganz normalen, nicht-hex Wert.
    """

    lookup = FakeLookup(name="Modulinfo")
    entry = FakeEntry(value="1.0.2")

    assert (
        metadata.entity_category(
            lookup,
            entry,
        )
        == "diagnostic"
    )


def test_has_numeric_value_true_for_plain_number():

    entry = FakeEntry(value="65.3")

    assert metadata.has_numeric_value(entry) is True


def test_has_numeric_value_false_for_placeholder():

    entry = FakeEntry(value="-")

    assert metadata.has_numeric_value(entry) is False


def test_has_numeric_value_handles_comma_decimal():
    """Manche NV-Werte verwenden ein Komma statt Punkt als
    Dezimaltrennzeichen.
    """

    entry = FakeEntry(value="65,3")

    assert metadata.has_numeric_value(entry) is True


def test_enum_translation_returns_readable_text():
    """Regressionstest fuer das Enum-Uebersetzungs-Feature: ein Wert
    mit bekannter (group, member, enum_value)-Kombination soll den
    lesbaren Text liefern statt der rohen Zahl.
    """

    entry = FakeEntry(
        value="0",
        unit=None,
        group=3,
        member=50,
    )

    enum_texts = {
        (3, 50, 0): "Standby",
        (3, 50, 1): "Heizprogramm 1",
    }

    assert (
        metadata.parsed_value(
            entry,
            "0",
            enum_texts,
        )
        == "Standby"
    )


def test_enum_translation_different_value_same_group():
    """Verschiedene Werte derselben (group, member)-Kombination
    sollen unterschiedliche Texte liefern - kein zufaelliger Treffer.
    """

    entry = FakeEntry(
        value="1",
        unit=None,
        group=3,
        member=50,
    )

    enum_texts = {
        (3, 50, 0): "Standby",
        (3, 50, 1): "Heizprogramm 1",
    }

    assert (
        metadata.parsed_value(
            entry,
            "1",
            enum_texts,
        )
        == "Heizprogramm 1"
    )


def test_enum_translation_falls_back_to_raw_value_without_match():
    """Ohne passenden Eintrag in enum_texts (z.B. unbekannter Wert,
    oder Katalog ohne enum_texts ueberhaupt) bleibt der Rohwert
    unveraendert - kein Crash, kein leerer String.
    """

    entry = FakeEntry(
        value="99",
        unit=None,
        group=3,
        member=50,
    )

    enum_texts = {
        (3, 50, 0): "Standby",
    }

    assert (
        metadata.parsed_value(
            entry,
            "99",
            enum_texts,
        )
        == "99"
    )


def test_enum_translation_none_enum_texts_keeps_raw_value():
    """Rueckwaertskompatibilitaet: ein Katalog ohne enum_texts
    (z.B. vor Einfuehrung des Features gespeichert) darf das
    Verhalten nicht aendern.
    """

    entry = FakeEntry(
        value="0",
        unit=None,
        group=3,
        member=50,
    )

    assert (
        metadata.parsed_value(
            entry,
            "0",
            None,
        )
        == "0"
    )


def test_enum_value_is_not_numeric():
    """Ein erfolgreich uebersetzter Enum-Wert gilt NICHT als
    numerisch (ein Statuscode ist kein Messwert) - verhindert
    state_class/Statistik ueber bedeutungslose Durchschnittswerte.
    """

    entry = FakeEntry(
        value="0",
        unit=None,
        group=3,
        member=50,
    )

    enum_texts = {
        (3, 50, 0): "Standby",
    }

    assert (
        metadata.has_numeric_value(
            entry,
            "0",
            enum_texts,
        )
        is False
    )


def test_enum_value_is_still_valid():
    """Auch wenn ein Enum-Wert nicht numerisch ist, ist er trotzdem
    "valid" - der Sensor zeigt ja einen sinnvollen Text, sollte also
    nicht als unverfuegbar/unbekannt behandelt werden.
    """

    entry = FakeEntry(
        value="0",
        unit=None,
        group=3,
        member=50,
    )

    enum_texts = {
        (3, 50, 0): "Standby",
    }

    assert (
        metadata.has_valid_value(
            entry,
            "0",
            enum_texts,
        )
        is True
    )


def test_state_class_none_for_enum_value():

    entry = FakeEntry(
        value="0",
        unit=None,
        group=3,
        member=50,
    )

    enum_texts = {
        (3, 50, 0): "Standby",
    }

    assert (
        metadata.state_class(
            entry,
            "0",
            enum_texts,
        )
        is None
    )


def test_state_class_measurement_for_temperature():

    entry = FakeEntry(
        value="65.3",
        unit="°C",
        name="TK_nvoTemp",
    )

    assert (
        metadata.state_class(entry, "65.3")
        == "measurement"
    )


def test_state_class_total_increasing_for_known_counter():
    """Bekannte, monoton steigende Zaehler (siehe
    TOTAL_INCREASING_NV_NAMES) bekommen TOTAL_INCREASING statt
    MEASUREMENT, damit HA sie korrekt fuer Langzeitstatistiken
    behandelt.
    """

    entry = FakeEntry(
        value="48925",
        unit="Std",
        name="PMX_eeBetrStd",
    )

    assert (
        metadata.state_class(entry, "48925")
        == "total_increasing"
    )


def test_device_class_temperature_for_celsius():

    entry = FakeEntry(value="65.3", unit="°C")

    assert (
        metadata.device_class(entry)
        == "temperature"
    )


def test_device_class_none_for_unknown_unit():

    entry = FakeEntry(value="1500", unit="rpm")

    assert metadata.device_class(entry) is None


def test_unit_translation_std_to_h():
    """Windhager liefert teils eigene Einheitenkuerzel ("Std" statt
    "h"), die HA nicht kennt.
    """

    assert metadata.translate_unit("Std") == "h"


def test_unit_translation_passes_through_unknown_units():

    assert metadata.translate_unit("°C") == "°C"


def test_unit_translation_none_stays_none():

    assert metadata.translate_unit(None) is None


def test_entry_enum_field_detected_without_text_translation():
    """Regressionstest fuer die API-'enum'-Feld-basierte Erkennung
    (2026-06-30): ein Eintrag mit entry.enum gesetzt soll als Enum
    erkannt werden (numeric=False), auch OHNE passenden Eintrag in
    enum_texts. Windhager nutzt mehrere typeId-Werte fuer Enums
    (mindestens 0 und 9 beobachtet) - das API-eigene 'enum'-Feld ist
    robuster als eine unvollstaendige typeId-Whitelist.
    """

    entry = FakeEntry(
        value="0",
        unit=None,
        group=4,
        member=13,
        enum=[0, 1, 2],
    )

    assert (
        metadata.is_enum_value(entry, "0", None)
        is True
    )
    assert (
        metadata.has_numeric_value(entry, "0", None)
        is False
    )
    assert (
        metadata.has_valid_value(entry, "0", None)
        is True
    )

    # Ohne Text-Uebersetzung bleibt der Rohwert sichtbar
    assert (
        metadata.parsed_value(entry, "0", None)
        == "0"
    )


def test_entry_enum_field_with_text_translation():
    """entry.enum UND eine passende enum_texts-Uebersetzung
    zusammen: der lesbare Text wird angezeigt.
    """

    entry = FakeEntry(
        value="0",
        unit=None,
        group=4,
        member=13,
        enum=[0, 1, 2],
    )

    enum_texts = {(4, 13, 0): "senden"}

    assert (
        metadata.parsed_value(
            entry,
            "0",
            enum_texts,
        )
        == "senden"
    )


def test_entry_enum_field_value_outside_known_range():
    """Ein Wert, der NICHT in entry.enum steht (z.B. wegen eines
    unerwarteten/neuen Anlagenzustands), soll NICHT faelschlich als
    Enum behandelt werden - bleibt als normaler numerischer Wert.
    """

    entry = FakeEntry(
        value="99",
        unit=None,
        group=4,
        member=13,
        enum=[0, 1, 2],
    )

    assert (
        metadata.is_enum_value(entry, "99", None)
        is False
    )
    assert (
        metadata.has_numeric_value(entry, "99", None)
        is True
    )


def test_no_entry_enum_field_is_not_treated_as_enum():
    """Normale numerische Werte (kein entry.enum gesetzt) bleiben
    unveraendert numerisch - keine Regression durch das neue Feature.
    """

    entry = FakeEntry(
        value="65.3",
        unit="°C",
        enum=None,
    )

    assert (
        metadata.is_enum_value(entry, "65.3", None)
        is False
    )
    assert (
        metadata.has_numeric_value(
            entry,
            "65.3",
            None,
        )
        is True
    )
