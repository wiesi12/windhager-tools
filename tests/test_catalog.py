"""Tests fuer lib/catalog.py.

Schwerpunkt: das Speicher-/Ladeformat-Roundtrip (inkl. enum_texts),
und die Rueckwaertskompatibilitaet zum AELTEREN Katalog-Format (reine
Modul-Liste statt {"modules": [...], "enum_texts": {...}}) - so muss
ein vor Einfuehrung des Enum-Features gespeicherter Katalog nicht neu
gecrawlt werden, nur weil sich das Format geaendert hat.
"""

import json
import tempfile
from pathlib import Path

from lib.catalog import (
    load_catalog,
    save_catalog,
)
from lib.models import (
    Entry,
    Function,
    Lookup,
    Module,
)


def _sample_module():

    entry = Entry(
        oid="/1/15/0/3/50/0",
        value="0",
        unit=None,
        type_id=9,
        write_protected=False,
        group=3,
        member=50,
        name="Betriebswahl",
    )

    lookup = Lookup(
        id=96,
        count=1,
        name="Betriebswahl",
    )
    lookup.entries.append(entry)

    function = Function(
        id=0,
        type=14,
        name="",
        locked=False,
    )
    function.lookups.append(lookup)

    module = Module(
        id=15,
        name="HK1 OG1/2",
        group="",
        subnet=1,
        program_id="",
        neuron_id="",
    )
    module.functions.append(function)

    return module


def test_save_and_load_roundtrip_preserves_modules():

    with tempfile.TemporaryDirectory() as tmpdir:

        catalog_path = (
            Path(tmpdir) / "catalog.json"
        )

        save_catalog(
            [_sample_module()],
            catalog_path,
        )

        modules, enum_texts = load_catalog(
            catalog_path
        )

        assert len(modules) == 1
        assert modules[0].name == "HK1 OG1/2"
        assert (
            modules[0].functions[0]
            .lookups[0]
            .entries[0]
            .value
            == "0"
        )


def test_save_and_load_roundtrip_preserves_enum_texts():

    with tempfile.TemporaryDirectory() as tmpdir:

        catalog_path = (
            Path(tmpdir) / "catalog.json"
        )

        enum_texts = {
            (3, 50, 0): "Standby",
            (3, 50, 1): "Heizprogramm 1",
        }

        save_catalog(
            [_sample_module()],
            catalog_path,
            enum_texts,
        )

        _, loaded_enum_texts = load_catalog(
            catalog_path
        )

        assert (
            loaded_enum_texts == enum_texts
        )


def test_load_old_format_without_enum_texts():
    """Regressionstest fuer Rueckwaertskompatibilitaet: ein Katalog
    im AELTEREN Format (reine Liste statt {"modules": ..., 
    "enum_texts": ...}) muss weiterhin korrekt laden, nur mit leeren
    enum_texts statt eines Fehlers.
    """

    with tempfile.TemporaryDirectory() as tmpdir:

        catalog_path = (
            Path(tmpdir) / "catalog_old.json"
        )

        from dataclasses import asdict

        old_format_data = [
            asdict(_sample_module())
        ]

        with catalog_path.open(
            "w",
            encoding="utf-8",
        ) as f:

            json.dump(
                old_format_data,
                f,
            )

        modules, enum_texts = load_catalog(
            catalog_path
        )

        assert len(modules) == 1
        assert modules[0].name == "HK1 OG1/2"
        assert enum_texts == {}


def test_save_without_enum_texts_defaults_to_empty():
    """save_catalog() ohne enum_texts-Argument (Rueckwaertskompati-
    bilitaet fuer Aufrufer, die das Feature noch nicht kennen) soll
    nicht crashen und ein leeres enum_texts speichern.
    """

    with tempfile.TemporaryDirectory() as tmpdir:

        catalog_path = (
            Path(tmpdir) / "catalog.json"
        )

        save_catalog(
            [_sample_module()],
            catalog_path,
        )

        _, enum_texts = load_catalog(
            catalog_path
        )

        assert enum_texts == {}


def test_load_corrupt_json_raises():
    """load_catalog() selbst soll bei kaputtem JSON eine Exception
    werfen (NICHT stillschweigend leere Daten liefern) - die
    eigentliche Fehlerbehandlung (loeschen + neu crawlen) passiert
    eine Ebene hoeher in WindhagerSystem.initialize(), nicht hier.
    """

    with tempfile.TemporaryDirectory() as tmpdir:

        catalog_path = (
            Path(tmpdir) / "corrupt.json"
        )

        catalog_path.write_text(
            "{ das ist kein valides JSON",
            encoding="utf-8",
        )

        try:

            load_catalog(catalog_path)

            assert False, (
                "load_catalog() haette eine "
                "Exception werfen muessen"
            )

        except json.JSONDecodeError:

            pass
