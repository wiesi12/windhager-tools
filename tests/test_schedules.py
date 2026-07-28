"""Tests fuer lib/schedules.py.

Schwerpunkt: die generische Erkennung von Zeitprogrammen ueber die von
der Box selbst gelieferte res/xml/StaticNav.xml-Ressource (keine von
uns gepflegte Gruppen-Liste, keine Modul-ID im Code) - siehe Docstring
in schedules.py fuer die Herleitung dieses Verfahrens (409 auf der
normalen Gruppen-Auflistung, einzelne Member aber direkt adressierbar).
"""

import requests

from lib.models import Function, Module
from lib.schedules import discover_schedules


STATIC_NAV_XML = """<?xml version="1.0" encoding="UTF-8"?>
<static_nav>
    <timeprogram gnmn="03:61">
        <text>
            <default>Zeitprogramm 1</default>
            <en>Heating program 1</en>
            <de>Zeitprogramm 1</de>
        </text>
    </timeprogram>
    <timeprogram gnmn="05:62">
        <text>
            <default>Warmwasser Legionellen Zeitprogramm</default>
            <en>DHW legionella clock program</en>
            <de>Warmwasser Legionellen Zeitprogramm</de>
        </text>
    </timeprogram>
    <errorlog gnmn="02:90">
        <text>
            <default>Stoerspeicher</default>
            <de>Stoerspeicher</de>
        </text>
    </errorlog>
</static_nav>
"""


class FakeResponse:

    def __init__(self, status_code):

        self.status_code = status_code


class FakeClient:
    """Simuliert client.lookup()/client.resource() fuer die Tests.

    responses: Pfad -> Antwort-Dict, oder int (HTTP-Fehlerstatus, wird
    als requests.HTTPError geworfen). Nicht gelistete Pfade werfen
    standardmaessig 409 (entspricht dem beobachteten Verhalten fuer
    ungueltige Positionen).
    """

    def __init__(
        self,
        responses,
        default_status=409,
        static_nav_xml=STATIC_NAV_XML,
    ):

        self.responses = responses
        self.default_status = default_status
        self.static_nav_xml = static_nav_xml
        self.calls = []

    def lookup(self, path):

        self.calls.append(path)

        result = self.responses.get(
            path,
            self.default_status,
        )

        if isinstance(result, int):

            error = requests.HTTPError()
            error.response = FakeResponse(result)
            raise error

        return result

    def resource(self, path):

        if path != "xml/StaticNav.xml":
            raise FileNotFoundError(path)

        if self.static_nav_xml is None:
            raise RuntimeError("simulierter Ladefehler")

        return self.static_nav_xml


def _module_with_function(
    module_id,
    function_id=0,
    function_type=14,
):

    function = Function(
        id=function_id,
        type=function_type,
        name="",
        locked=False,
    )

    module = Module(
        id=module_id,
        name=f"Modul {module_id}",
        group="",
        subnet=1,
        program_id="",
        neuron_id="",
    )
    module.functions.append(function)

    return module


def test_discover_schedules_uses_static_nav_positions():

    module = _module_with_function(15)

    client = FakeClient(
        {
            "1/15/0/3/61": {
                "OID": "/1/15/0/3/61/0",
                "typeId": 30,
            },
            "1/15/0/5/62": {
                "OID": "/1/15/0/5/62/0",
                "typeId": 30,
            },
        }
    )

    schedules = discover_schedules(client, [module])

    assert sorted(s["oid"] for s in schedules) == [
        "/1/15/0/3/61/0",
        "/1/15/0/5/62/0",
    ]

    by_oid = {s["oid"]: s for s in schedules}

    assert (
        by_oid["/1/15/0/3/61/0"]["name"] == "Zeitprogramm 1"
    )
    assert (
        by_oid["/1/15/0/5/62/0"]["name"]
        == "Warmwasser Legionellen Zeitprogramm"
    )
    assert by_oid["/1/15/0/3/61/0"]["lookup_id"] == 3
    assert by_oid["/1/15/0/3/61/0"]["member_id"] == 61
    assert by_oid["/1/15/0/3/61/0"]["module"] is module


def test_discover_schedules_uses_language_specific_name():

    module = _module_with_function(15)

    client = FakeClient(
        {
            "1/15/0/3/61": {
                "OID": "/1/15/0/3/61/0",
                "typeId": 30,
            },
        }
    )

    schedules = discover_schedules(client, [module], language="en")

    assert schedules[0]["name"] == "Heating program 1"


def test_discover_schedules_falls_back_to_default_when_language_missing():

    module = _module_with_function(15)

    client = FakeClient(
        {
            "1/15/0/3/61": {
                "OID": "/1/15/0/3/61/0",
                "typeId": 30,
            },
        }
    )

    # "fr" ist in STATIC_NAV_XML fuer diesen Eintrag nicht vorhanden -
    # muss auf <default> zurueckfallen statt zu crashen.
    schedules = discover_schedules(client, [module], language="fr")

    assert schedules[0]["name"] == "Zeitprogramm 1"


def test_discover_schedules_ignores_non_schedule_type_id():

    module = _module_with_function(15)

    client = FakeClient(
        {
            "1/15/0/3/61": {
                "OID": "/1/15/0/3/61/0",
                "typeId": 13,
            },
        }
    )

    schedules = discover_schedules(client, [module])

    assert schedules == []


def test_discover_schedules_treats_unexpected_errors_as_skip():
    """Ein unerwarteter Fehlerstatus (nicht 409) fuer EINE Position
    darf die anderen, gueltigen Treffer nicht verhindern."""

    module = _module_with_function(15)

    client = FakeClient(
        {
            "1/15/0/3/61": {
                "OID": "/1/15/0/3/61/0",
                "typeId": 30,
            },
            "1/15/0/5/62": 500,
        }
    )

    schedules = discover_schedules(client, [module])

    assert len(schedules) == 1
    assert schedules[0]["oid"] == "/1/15/0/3/61/0"


def test_discover_schedules_returns_empty_when_static_nav_unavailable():
    """Falls StaticNav.xml nicht geladen werden kann (z.B. andere
    Firmware-Version), soll gar nicht erst gescannt werden - kein
    Crash, einfach keine Zeitprogramme gefunden."""

    module = _module_with_function(15)

    client = FakeClient({}, static_nav_xml=None)

    schedules = discover_schedules(client, [module])

    assert schedules == []
    # Ohne Positionsliste darf erst gar kein lookup()-Call gegen die
    # Box ausgeloest werden.
    assert client.calls == []


def test_discover_schedules_across_multiple_modules():

    module_a = _module_with_function(15)
    module_b = _module_with_function(16)

    client = FakeClient(
        {
            "1/15/0/3/61": {
                "OID": "/1/15/0/3/61/0",
                "typeId": 30,
            },
            "1/16/0/3/61": {
                "OID": "/1/16/0/3/61/0",
                "typeId": 30,
            },
        }
    )

    schedules = discover_schedules(client, [module_a, module_b])

    assert sorted(s["oid"] for s in schedules) == [
        "/1/15/0/3/61/0",
        "/1/16/0/3/61/0",
    ]
