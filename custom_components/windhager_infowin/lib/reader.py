from .models import Entry, NvEntry

import json
import logging

_LOGGER = logging.getLogger(__name__)


def _parse_enum_field(raw_enum):
    """Das "enum"-Feld der API parsen (z.B. "[0,1,2,3,4,5]" als
    String, nicht als echtes JSON-Array innerhalb des umgebenden
    JSON-Objekts - Windhager liefert es offenbar als Text).

    Liefert None bei fehlendem/leerem/unparsbarem Wert, statt eine
    Exception zu werfen - ein nicht erkennbares enum-Feld soll den
    gesamten Poll nicht zum Absturz bringen, sondern nur dazu fuehren,
    dass dieser eine Eintrag wie ein normaler (Nicht-Enum-)Wert
    behandelt wird.
    """

    if not raw_enum:
        return None

    try:

        parsed = json.loads(raw_enum)

    except (
        json.JSONDecodeError,
        TypeError,
    ):

        return None

    if not isinstance(parsed, list):
        return None

    return parsed


def read_lookup(client, module, function, lookup, fetch_nv_values=False):
    """Eine Lookup-Gruppe (OID-Entries oder NV's) lesen.

    fetch_nv_values=False (Default, fuer den haeufigen 30s-Poll):
    NV's bekommen NUR ihre Struktur (Name, Index, SNVT-Infos) aus der
    "Listen"-Abfrage - kein zusaetzlicher API-Call pro NV. Ihr "value"
    bleibt dabei der Platzhalter aus der Listen-Antwort (typischerweise
    "-"), da diese Abfrage grundsaetzlich keinen aktuellen Wert liefert.

    fetch_nv_values=True (fuer den selteneren NV-Poll, z.B. alle 10
    Minuten): pro gefundener NV wird zusaetzlich ein gezielter Call
    mit dem nvIndex als 5. Pfadsegment gemacht, der den tatsaechlichen
    aktuellen Wert liefert. Das verursacht einen API-Call PRO NV (bei
    "NV's"-Lookups mit oft 100+ Eintraegen entsprechend viele Calls),
    daher bewusst nicht im haeufigen Poll-Zyklus.
    """

    data = client.lookup(
        f"1/{module.id}/{function.id}/{lookup.id}"
    )

    entries = []

    for item in data:

        if "OID" in item:

            entries.append(
                Entry(
                    oid=item["OID"],

                    value=item.get("value"),

                    unit=item.get("unit"),
                    unit_id=item.get("unitId"),

                    type_id=item.get("typeId"),
                    subtype_id=item.get("subtypeId"),

                    group=item.get("groupNr"),
                    member=item.get("memberNr"),

                    min_value=item.get("minValue"),
                    max_value=item.get("maxValue"),

                    step=item.get("step"),
                    step_id=item.get("stepId"),

                    timestamp=item.get("timestamp"),

                    enum=_parse_enum_field(
                        item.get("enum")
                    ),

                    write_protected=item.get("writeProt"),

                    name="",
                )
            )

        elif "nvName" in item:

            nv_index = item["nvIndex"]

            value = item.get("value")
            unit = item.get("unit")

            if fetch_nv_values:

                try:

                    detail = read_nv_value(
                        client,
                        module,
                        function,
                        lookup,
                        nv_index,
                    )

                    value = detail.get("value", value)
                    unit = detail.get("unit", unit)

                except Exception as exc:

                    # Wenn der Detail-Call fehlschlaegt (z.B.
                    # Netzwerkfehler, NV temporaer nicht erreichbar),
                    # lieber mit dem Platzhalterwert aus der Listen-
                    # Abfrage weitermachen statt den gesamten Poll
                    # abzubrechen - aber den Fehler LOGGEN, damit er
                    # nicht stillschweigend verschwindet (frueher
                    # "except Exception: pass" ohne jedes Logging).
                    _LOGGER.debug(
                        "NV-Detailabfrage fehlgeschlagen fuer "
                        "%s (Modul %s, nvIndex %s): %s",
                        item.get("nvName"),
                        module.id,
                        nv_index,
                        exc,
                    )

            entries.append(
                NvEntry(
                    index=nv_index,
                    name=item["nvName"],
                    snvt_name=item.get("snvtName"),
                    snvt_index=item.get("snvtIndex"),
                    value=value,
                    unit=unit,
                )
            )

    return entries


def read_nv_value(client, module, function, lookup, nv_index):
    """Aktuellen Live-Wert einer einzelnen NV-Variable abrufen.

    Die "Listen"-Abfrage (ohne nvIndex) liefert ein Array mit der
    Struktur aller NV's einer Lookup-Gruppe, aber keinen aktuellen
    Wert. Dieser gezielte Call mit nvIndex als zusaetzlichem
    Pfadsegment liefert dagegen ein EINZELNES JSON-Objekt (kein
    Array!) mit dem vollstaendigen Datensatz inkl. echtem "value".
    """

    result = client.lookup(
        f"1/{module.id}/{function.id}/{lookup.id}/{nv_index}"
        f"?count=10&offset=0"
    )

    if isinstance(result, list):

        # Falls die API doch mal ein Array liefert (z.B. bei
        # anderen Firmware-Versionen), trotzdem robust bleiben.
        return result[0] if result else {}

    return result or {}