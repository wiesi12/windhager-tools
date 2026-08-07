import logging
from xml.etree import ElementTree

import requests

from .resources import DEFAULT_LANGUAGE


_LOGGER = logging.getLogger(__name__)

# Windhager legt Zeitprogramme (Schaltzeiten) in einem eigenen
# Adressraum ab, der NICHT Teil der normal auflistbaren Lookup-Gruppen
# ist: discover_lookups() (der bestehende 3-Segment-Call) listet die
# Zeitprogramm-Gruppen dort nicht auf, und eine Gruppen-Auflistung
# dieser Adressen liefert einen 409 Conflict. Einzelne Member SIND aber
# direkt adressierbar und liefern zuverlaessig entweder die Daten (200)
# oder 409 fuer eine ungueltige Member-Nummer.
#
# Statt einer von uns selbst gepflegten Liste "bekannter" Gruppen-IDs
# nutzt diese Erkennung eine von der Box selbst mitgelieferte,
# vollstaendige Ressource: res/xml/StaticNav.xml listet ALLE
# Zeitprogramm-Positionen (Gruppe:Member) samt echtem, mehrsprachigem
# Namen (z.B. "03:61" -> "Zeitprogramm 1", "05:62" -> "Warmwasser
# Legionellen Zeitprogramm"). Verifiziert am 2026-07-28 an einer Anlage
# mit 3 Heizkreisen + Warmwasserkreis (7 Positionen gefunden, u.a. ein
# "Sonderzeitprogramm" unter Gruppe 4, das eine reine Gruppen-Whitelist
# nie gefunden haette).
#
# Diese Positionsliste wird dann gegen JEDE Funktion JEDES Moduls
# geprueft (kein Funktionstyp-Filter mehr noetig - ungueltige
# Kombinationen liefern einfach 409). Damit ist weder eine Modul-ID
# noch eine Gruppen-ID hier hardcodiert - alles kommt von der Box
# selbst, und die Erkennung aktualisiert sich automatisch, falls
# Windhager diese Ressource in einer neueren Firmware erweitert.
SCHEDULE_TYPE_ID = 30
SCHEDULE_SUBTYPE_ID = 14


def _load_timeprogram_positions(client, language):
    """res/xml/StaticNav.xml laden und alle <timeprogram>-Eintraege
    parsen.

    Format pro Eintrag:
        <timeprogram gnmn="03:61">
            <text><de>Zeitprogramm 1</de><en>...</en>...</text>
        </timeprogram>

    Liefert eine Liste von (group, member, name)-Tupeln. Bei Fehlern
    (z.B. eine Firmware-Version ohne diese Ressource) wird eine leere
    Liste geliefert statt einer Exception - Discovery findet dann
    schlicht keine Zeitprogramme, statt den gesamten Setup-Vorgang
    abzubrechen.
    """

    try:

        root = ElementTree.fromstring(
            client.resource("xml/StaticNav.xml")
        )

    except Exception as exc:

        _LOGGER.debug(
            "StaticNav.xml konnte nicht geladen/geparst werden: %s",
            exc,
        )

        return []

    positions = []

    for entry in root.findall("timeprogram"):

        group_str, member_str = entry.attrib["gnmn"].split(":")

        text_el = entry.find("text")

        name_el = (
            text_el.find(language)
            if text_el is not None
            else None
        )

        if name_el is None or not (name_el.text or "").strip():

            name_el = (
                text_el.find("default")
                if text_el is not None
                else None
            )

        name = (
            (name_el.text if name_el is not None else None)
            or f"Zeitprogramm {member_str}"
        )

        positions.append(
            (
                int(group_str),
                int(member_str),
                name,
            )
        )

    return positions


def discover_schedules(client, modules, language=DEFAULT_LANGUAGE):
    """Zeitprogramme ueber ALLE Module/Funktionen finden.

    Nutzt die von res/xml/StaticNav.xml gelieferte Positionsliste
    (siehe _load_timeprogram_positions) - keine Modul-ID und keine
    Gruppen-ID ist hier von uns hardcodiert. Liefert eine Liste von
    Dicts {module, function_id, lookup_id, member_id, oid, name} -
    "module" ist das echte Module-Objekt (fuer Device-Zuordnung),
    "name" der von der Box selbst gelieferte, echte Anzeigename.
    """

    positions = _load_timeprogram_positions(client, language)

    if not positions:
        return []

    schedules = []

    for module in modules:

        for function in module.functions:

            for group, member, name in positions:

                path = (
                    f"1/{module.id}/{function.id}/{group}/{member}"
                )

                try:

                    data = client.lookup(path)

                except requests.HTTPError as exc:

                    status = (
                        exc.response.status_code
                        if exc.response is not None
                        else None
                    )

                    if status in (404, 409):
                        # 404/409: Position gilt fuer diese Funktion
                        # nicht - normal, kein Fehler.
                        continue

                    _LOGGER.debug(
                        "Zeitprogramm-Scan: unerwarteter Fehler bei "
                        "%s: %s",
                        path,
                        exc,
                    )
                    continue

                if isinstance(data, list):
                    data = data[0] if data else {}

                if data.get("typeId") != SCHEDULE_TYPE_ID:
                    continue

                oid = data.get("OID")

                if not oid:
                    continue

                schedules.append(
                    {
                        "module": module,
                        "function_id": function.id,
                        "lookup_id": group,
                        "member_id": member,
                        "oid": oid,
                        "name": name,
                    }
                )

    return schedules
