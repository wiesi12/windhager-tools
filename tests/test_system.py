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

import pytest

import lib.system as system_module
from lib.models import Module


class FakeClient:
    pass


class FakeScheduleClient:
    """FakeClient fuer poll_schedules()/write_schedule() - simuliert
    get_object()/write_object() ohne echte HTTP-Requests."""

    def __init__(self):

        self.get_object_responses = {}
        self.get_object_raises = set()
        self.write_object_calls = []

    def get_object(self, oid):

        if oid in self.get_object_raises:
            raise RuntimeError("simulierter Netzwerkfehler")

        return self.get_object_responses[oid]

    def write_object(self, **kwargs):

        self.write_object_calls.append(kwargs)


def _schedule_entry(module_id=15, oid="/1/15/0/3/61/0"):

    module = Module(
        id=module_id,
        name=f"HK{module_id}",
        group="",
        subnet=1,
        program_id="",
        neuron_id="",
    )

    return {
        "module": module,
        "function_id": 0,
        "lookup_id": 3,
        "member_id": 61,
        "oid": oid,
        "name": "Zeitprogramm 1",
    }


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


def test_poll_schedules_returns_value_per_oid():

    client = FakeScheduleClient()
    schedule = _schedule_entry()
    client.get_object_responses[schedule["oid"]] = {
        "value": [
            {
                "switchPoints": [{"time": "05:45", "value": 12}],
                "weekdays": ["Mo"],
            }
        ],
    }

    system = system_module.WindhagerSystem(client)
    system.poller = "dummy"  # initialize() nicht erneut anstossen
    system.schedules = [schedule]

    result = system.poll_schedules()

    assert result == {
        schedule["oid"]: client.get_object_responses[schedule["oid"]]
    }


def test_poll_schedules_skips_failing_entries_without_crashing():
    """Ein fehlschlagender get_object()-Call fuer EIN Zeitprogramm
    darf die anderen nicht verhindern - analog zur bestehenden
    NV-Fehlerbehandlung in reader.read_lookup()."""

    client = FakeScheduleClient()

    ok_schedule = _schedule_entry(
        module_id=15,
        oid="/1/15/0/3/61/0",
    )
    failing_schedule = _schedule_entry(
        module_id=16,
        oid="/1/16/0/3/61/0",
    )

    client.get_object_responses[ok_schedule["oid"]] = {"value": []}
    client.get_object_raises.add(failing_schedule["oid"])

    system = system_module.WindhagerSystem(client)
    system.poller = "dummy"
    system.schedules = [ok_schedule, failing_schedule]

    result = system.poll_schedules()

    assert result == {ok_schedule["oid"]: {"value": []}}


def test_write_schedule_derives_query_params_from_schedule():

    client = FakeScheduleClient()
    schedule = _schedule_entry()

    system = system_module.WindhagerSystem(client)
    system.poller = "dummy"
    system.schedules = [schedule]

    system.write_schedule(
        schedule["oid"],
        blocks=[
            {
                "switch_points": [{"time": "05:45", "value": 12}],
                "weekdays": ["Mo"],
            }
        ],
    )

    assert len(client.write_object_calls) == 1

    call = client.write_object_calls[0]

    assert call["node_id"] == 15
    assert call["function_id"] == 0
    assert call["oid_path"] == "3/61"
    assert call["oid"] == schedule["oid"]
    assert call["subtype_id"] == 14
    assert call["type_id"] == 30
    assert call["value"] == [
        {
            "switchPoints": [{"time": "05:45", "value": 12}],
            "weekdays": ["Mo"],
        }
    ]


def test_write_schedule_supports_multiple_blocks():
    """Windhager erlaubt mehrere Schaltgruppen mit unterschiedlichen
    Wochentagen (z.B. Warmwasser-Zeitprogramm: Mo-Sa vs. So mit
    unterschiedlichen Werten) - verifiziert per Browser-Devtools."""

    client = FakeScheduleClient()
    schedule = _schedule_entry()

    system = system_module.WindhagerSystem(client)
    system.poller = "dummy"
    system.schedules = [schedule]

    system.write_schedule(
        schedule["oid"],
        blocks=[
            {
                "switch_points": [
                    {"time": "06:00", "value": 55},
                    {"time": "22:00", "value": 10},
                ],
                "weekdays": ["Mo", "Tu", "We", "Th", "Fr", "Sa"],
            },
            {
                "switch_points": [
                    {"time": "06:00", "value": 65},
                    {"time": "22:00", "value": 10},
                ],
                "weekdays": ["Su"],
            },
        ],
    )

    call = client.write_object_calls[0]

    assert call["value"] == [
        {
            "switchPoints": [
                {"time": "06:00", "value": 55},
                {"time": "22:00", "value": 10},
            ],
            "weekdays": ["Mo", "Tu", "We", "Th", "Fr", "Sa"],
        },
        {
            "switchPoints": [
                {"time": "06:00", "value": 65},
                {"time": "22:00", "value": 10},
            ],
            "weekdays": ["Su"],
        },
    ]


def test_write_schedule_raises_for_unknown_oid():

    client = FakeScheduleClient()

    system = system_module.WindhagerSystem(client)
    system.poller = "dummy"
    system.schedules = []

    with pytest.raises(ValueError):

        system.write_schedule(
            "/1/99/0/3/61/0",
            blocks=[],
        )
