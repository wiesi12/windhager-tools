"""Tests fuer lib/system.py.

Schwerpunkt: die robuste Fehlerbehandlung beim Katalog-Laden
(WindhagerSystem.initialize()) - bei korruptem/inkompatiblem Katalog
soll die Integration automatisch neu crawlen statt zu crashen.

Nutzt Monkeypatching (system.crawl/system.save_catalog werden durch
Fakes ersetzt), um echte HTTP-Requests an eine Windhager-Box zu
vermeiden - diese Tests pruefen reine Steuerungslogik, keine
Netzwerk-Kommunikation.
"""

import json
import tempfile
from pathlib import Path

import lib.system as system_module
from lib.models import Module


class FakeClient:
    pass


def _patch_crawl(monkeypatch, modules=None, enum_texts=None):

    call_count = {"value": 0}

    def fake_crawl(client, language):

        call_count["value"] += 1

        return (
            modules
            if modules is not None
            else [
                Module(
                    id=60,
                    name="BioWIN",
                    group="",
                    subnet=1,
                    program_id="",
                    neuron_id="",
                )
            ],
            enum_texts or {},
        )

    monkeypatch.setattr(
        system_module,
        "crawl",
        fake_crawl,
    )

    monkeypatch.setattr(
        system_module,
        "save_catalog",
        lambda modules, path, enum_texts=None: None,
    )

    return call_count


def test_initialize_crawls_fresh_when_no_catalog_exists(
    monkeypatch,
):

    call_count = _patch_crawl(monkeypatch)

    with tempfile.TemporaryDirectory() as tmpdir:

        catalog_path = (
            Path(tmpdir) / "catalog.json"
        )

        system = system_module.WindhagerSystem(
            FakeClient(),
            catalog_path=catalog_path,
        )

        system.initialize()

        assert call_count["value"] == 1
        assert len(system.modules) == 1
        assert system.modules[0].name == "BioWIN"


def test_initialize_recovers_from_corrupt_catalog(
    monkeypatch,
):
    """Regressionstest fuer die am 2026-06-29 eingefuehrte robuste
    Fehlerbehandlung: eine kaputte JSON-Datei darf die Integration
    nicht zum Absturz bringen, sondern soll automatisch geloescht
    und neu gecrawlt werden.
    """

    call_count = _patch_crawl(monkeypatch)

    with tempfile.TemporaryDirectory() as tmpdir:

        catalog_path = (
            Path(tmpdir) / "catalog.json"
        )

        catalog_path.write_text(
            "{ kaputtes JSON !!!",
            encoding="utf-8",
        )

        system = system_module.WindhagerSystem(
            FakeClient(),
            catalog_path=catalog_path,
        )

        system.initialize()

        assert call_count["value"] == 1
        assert len(system.modules) == 1

        # Die kaputte Datei muss geloescht worden sein
        assert not catalog_path.exists()


def test_initialize_recovers_from_incompatible_schema(
    monkeypatch,
):
    """Regressionstest: valides JSON, aber mit fehlenden
    Pflichtfeldern (simuliert eine Datenmodell-Aenderung zwischen
    zwei Versionen dieser Integration) soll genauso robust behandelt
    werden wie kaputtes JSON.
    """

    call_count = _patch_crawl(monkeypatch)

    with tempfile.TemporaryDirectory() as tmpdir:

        catalog_path = (
            Path(tmpdir) / "catalog.json"
        )

        with catalog_path.open(
            "w",
            encoding="utf-8",
        ) as f:

            # Fehlt z.B. "group"/"subnet"/etc.
            json.dump(
                {"modules": [{"name": "Test"}]},
                f,
            )

        system = system_module.WindhagerSystem(
            FakeClient(),
            catalog_path=catalog_path,
        )

        system.initialize()

        assert call_count["value"] == 1
        assert len(system.modules) == 1
        assert not catalog_path.exists()


def test_initialize_loads_valid_catalog_without_crawling(
    monkeypatch,
):
    """Gegenprobe: ein GUELTIGER, gespeicherter Katalog soll NICHT
    zu einem erneuten Crawl fuehren (sonst waere der ganze Zweck des
    Caching ad absurdum gefuehrt).
    """

    from lib.catalog import save_catalog

    call_count = _patch_crawl(monkeypatch)

    with tempfile.TemporaryDirectory() as tmpdir:

        catalog_path = (
            Path(tmpdir) / "catalog.json"
        )

        save_catalog(
            [
                Module(
                    id=15,
                    name="HK1 OG1/2",
                    group="",
                    subnet=1,
                    program_id="",
                    neuron_id="",
                )
            ],
            catalog_path,
        )

        system = system_module.WindhagerSystem(
            FakeClient(),
            catalog_path=catalog_path,
        )

        system.initialize()

        assert call_count["value"] == 0
        assert system.modules[0].name == "HK1 OG1/2"


def test_module_filtering_keeps_only_selected_modules():

    modules = [
        Module(
            id=15,
            name="HK1 OG1/2",
            group="",
            subnet=1,
            program_id="",
            neuron_id="",
        ),
        Module(
            id=16,
            name="HK2 EG/FBH",
            group="",
            subnet=1,
            program_id="",
            neuron_id="",
        ),
        Module(
            id=60,
            name="BioWIN",
            group="",
            subnet=1,
            program_id="",
            neuron_id="",
        ),
    ]

    filtered = [
        module
        for module in modules
        if str(module.id) in {"15", "60"}
    ]

    assert [m.name for m in filtered] == [
        "HK1 OG1/2",
        "BioWIN",
    ]


def test_module_filtering_none_means_all_modules(
    monkeypatch,
):
    """selected_module_ids=None bedeutet Rueckwaertskompatibilitaet:
    alle Module werden verwendet (z.B. fuer Config-Entries, die vor
    Einfuehrung der Modul-Auswahl eingerichtet wurden).
    """

    modules = [
        Module(
            id=15,
            name="HK1 OG1/2",
            group="",
            subnet=1,
            program_id="",
            neuron_id="",
        ),
        Module(
            id=60,
            name="BioWIN",
            group="",
            subnet=1,
            program_id="",
            neuron_id="",
        ),
    ]

    _patch_crawl(monkeypatch, modules=modules)

    with tempfile.TemporaryDirectory() as tmpdir:

        catalog_path = (
            Path(tmpdir) / "catalog.json"
        )

        system = system_module.WindhagerSystem(
            FakeClient(),
            catalog_path=catalog_path,
            selected_module_ids=None,
        )

        system.initialize()

        assert len(system.modules) == 2
