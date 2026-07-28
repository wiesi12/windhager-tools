from collections import Counter
import copy
import logging
from pathlib import Path

from .catalog import (
    load_catalog,
    save_catalog,
)
from .crawler import crawl
from .nv_groups import filter_nv_entries
from .poller import Poller
from .resources import DEFAULT_LANGUAGE
from .schedules import (
    SCHEDULE_SUBTYPE_ID,
    SCHEDULE_TYPE_ID,
    discover_schedules,
)


_LOGGER = logging.getLogger(__name__)


def _filter_modules_by_groups(
    modules,
    selected_groups_by_module,
):
    """Eine KOPIE der Module-Liste liefern, bei der pro Modul nur die
    in selected_groups_by_module gelisteten Lookup-Gruppen erhalten
    bleiben. Lookup-Gruppen OHNE Namen (lookup.name == "") werden
    immer erhalten - sie hatten im Config-Flow keine eigene Checkbox
    (siehe config_flow._current_module_lookup_keys()) und sollten
    daher nicht durch eine fehlende Erwaehnung in der Auswahl
    versehentlich herausgefiltert werden.

    Arbeitet auf einer tiefen Kopie (copy.deepcopy), damit der
    aufrufende Code (z.B. der bereits geladene/gecachte volle
    Katalog) unverändert bleibt, falls dieselben Modul-Objekte
    anderswo noch referenziert werden.
    """

    filtered_modules = []

    for module in modules:

        group_keys = selected_groups_by_module.get(
            str(module.id)
        )

        # Kein Eintrag fuer dieses Modul in der Auswahl (z.B. weil
        # die Config-Entry vor Einfuehrung der Gruppen-Feinauswahl
        # erstellt wurde) -> Modul unveraendert, mit allen Gruppen,
        # uebernehmen.
        if group_keys is None:

            filtered_modules.append(module)

            continue

        module_copy = copy.deepcopy(module)

        for function in module_copy.functions:

            function.lookups = [
                lookup
                for lookup in function.lookups
                if not lookup.name
                or f"{function.type}:{lookup.id}"
                in group_keys
            ]

        filtered_modules.append(module_copy)

    return filtered_modules


class WindhagerSystem:

    def __init__(
        self,
        client,
        catalog_path="catalog.json",
        language=DEFAULT_LANGUAGE,
        selected_module_ids=None,
        selected_groups_by_module=None,
        selected_nv_groups=None,
        boiler_module_id=None,
    ):

        self.client = client
        self.catalog_path = Path(catalog_path)
        self.language = language

        # None bedeutet "alle Module"/"alle Gruppen"/"alle NV-Gruppen"
        self.selected_module_ids = selected_module_ids
        self.selected_groups_by_module = (
            selected_groups_by_module
        )
        # Liste von NV-Gruppen-Keys (z.B. ["nv_group_temperatures",
        # "nv_group_counters"]). None = alle NV-Gruppen behalten
        # (Rueckwaertskompatibilitaet).
        self.selected_nv_groups = selected_nv_groups

        # Modul-ID des Waermeerzeugers, vom Nutzer im Options Flow
        # gewaehlt (siehe config_flow.py::async_step_select_boiler) -
        # dient den Plattform-Dateien als via_device-Ziel fuer die
        # Geraete-Hierarchie. None = keine Hierarchie (flache
        # Geraete-Struktur, bisheriges Verhalten). Bewusst KEINE
        # automatische Erkennung: manche Waermeerzeuger (z.B. BioWIN)
        # haben keinen aussagekraeftigen eigenen Funktionstyp, jeder
        # Rateversuch waere nur ein verstecktes Hardcoding.
        self.boiler_module_id = boiler_module_id

        self.modules = None
        self.poller = None

        self.oid_map = {}
        self.enum_texts = {}
        self.schedules = []

    def initialize(self):

        all_modules = None
        enum_texts = {}

        if self.catalog_path.exists():

            print("Lade Katalog...")

            try:

                all_modules, enum_texts = load_catalog(
                    self.catalog_path
                )

            except Exception as error:  # noqa: BLE001 - bewusst breit,

                # da load_catalog() je nach Korruptionsart ganz
                # unterschiedliche Fehler werfen kann (KeyError bei
                # fehlenden Feldern, json.JSONDecodeError bei kaputter
                # Datei, etc.). In JEDEM Fall ist die pragmatische,
                # sichere Reaktion dieselbe: den unbrauchbaren Katalog
                # verwerfen und neu crawlen, statt die gesamte
                # Integration mit einem Crash zu blockieren. Das deckt
                # insbesondere den Fall ab, dass sich unser eigenes
                # Datenmodell (Module/Function/Lookup/Entry) zwischen
                # zwei Versionen dieser Integration geaendert hat und
                # ein aelterer, gespeicherter Katalog nicht mehr zum
                # aktuellen Code passt.

                print(
                    f"Katalog beschaedigt oder inkompatibel "
                    f"({error}) - lösche und crawle neu..."
                )

                self.catalog_path.unlink(
                    missing_ok=True,
                )

        if all_modules is None:

            print("Starte Discovery...")

            all_modules, enum_texts = crawl(
                self.client,
                self.language,
            )

            # WICHTIG: der VOLLSTAENDIGE, ungefilterte Katalog wird
            # gespeichert - nicht nur die ausgewaehlten Module. Wuerde
            # der Nutzer seine Modul-Auswahl spaeter aendern (siehe
            # Options-Flow), waeren sonst die abgewaehlten Module
            # dauerhaft verloren und ein erneuter, vollstaendiger
            # Discovery-Crawl noetig, um sie wieder verfuegbar zu
            # machen.
            save_catalog(
                all_modules,
                self.catalog_path,
                enum_texts,
            )

        self.enum_texts = enum_texts

        if self.selected_module_ids is None:

            self.modules = all_modules

        else:

            self.modules = [
                module
                for module in all_modules
                if str(module.id)
                in self.selected_module_ids
            ]

        if self.selected_groups_by_module is not None:

            self.modules = _filter_modules_by_groups(
                self.modules,
                self.selected_groups_by_module,
            )

        # NV-Gruppen-Filterung: innerhalb jedes NV-Lookups nur die
        # gewaehlten snvt-Gruppen behalten.
        if self.selected_nv_groups is not None:

            for module in self.modules:

                for function in module.functions:

                    for lookup in function.lookups:

                        if lookup.name == "NV's":

                            lookup.entries = filter_nv_entries(
                                lookup.entries,
                                self.selected_nv_groups,
                            )

        self.poller = Poller(
            self.client,
            self.modules,
        )

        self.build_oid_map()

        # Zeitprogramme sind bewusst NICHT Teil des gecachten Katalogs
        # (siehe schedules.py) - der Scan ist klein/schnell genug, um
        # bei jedem Start erneut zu laufen, statt das bestehende,
        # getestete Katalog-Speicherformat anzufassen.
        self.schedules = discover_schedules(
            self.client,
            self.modules,
            self.language,
        )

    def build_oid_map(self):

        self.oid_map = {}

        for module in self.modules:

            for function in module.functions:

                for lookup in function.lookups:

                    for entry in lookup.entries:

                        if hasattr(entry, "oid"):

                            self.oid_map[entry.oid] = {
                                "module": module,
                                "function": function,
                                "lookup": lookup,
                                "entry": entry,
                            }

                        elif hasattr(entry, "index"):

                            # NvEntry hat kein oid, sondern einen pro-
                            # Modul eindeutigen index. Daraus einen
                            # eindeutigen, stabilen Schluessel bauen,
                            # damit NV-Eintraege wie normale OID-
                            # Eintraege als Sensor behandelt werden
                            # koennen.
                            nv_key = f"nv:{module.id}:{entry.index}"

                            self.oid_map[nv_key] = {
                                "module": module,
                                "function": function,
                                "lookup": lookup,
                                "entry": entry,
                            }

    def statistics(self):

        modules = len(self.modules)

        functions = 0
        lookups = 0
        entries = 0

        for module in self.modules:

            functions += len(module.functions)

            for function in module.functions:

                lookups += len(function.lookups)

                for lookup in function.lookups:

                    entries += len(lookup.entries)

        return {
            "modules": modules,
            "functions": functions,
            "lookups": lookups,
            "entries": entries,
        }

    def validate(self):

        stats = self.statistics()

        duplicate_oids = 0
        unnamed_lookups = 0
        unnamed_entries = 0

        oids = Counter()

        for module in self.modules:

            for function in module.functions:

                for lookup in function.lookups:

                    if not lookup.name:

                        unnamed_lookups += 1

                    for entry in lookup.entries:

                        if hasattr(entry, "oid"):

                            oids[entry.oid] += 1

                            if not entry.name:

                                unnamed_entries += 1

        duplicate_oids = sum(
            1
            for count in oids.values()
            if count > 1
        )

        print()

        print("=== CATALOG ===")
        print(f"Modules:   {stats['modules']}")
        print(f"Functions: {stats['functions']}")
        print(f"Lookups:   {stats['lookups']}")
        print(f"Entries:   {stats['entries']}")

        print()

        print("=== VALIDATION ===")
        print(
            f"Duplicate OIDs: {duplicate_oids}"
        )
        print(
            f"Lookups without name: {unnamed_lookups}"
        )
        print(
            f"Entries without name: {unnamed_entries}"
        )

    def poll(self):

        if self.poller is None:

            self.initialize()

        return self.poller.poll()

    def poll_nv(self):

        if self.poller is None:

            self.initialize()

        return self.poller.poll_nv()

    def poll_schedules(self):
        """Aktuelle Werte aller entdeckten Zeitprogramme abrufen.

        Ein fehlschlagender Call fuer ein einzelnes Zeitprogramm
        (z.B. voruebergehender Netzwerkfehler) bricht nicht den
        gesamten Poll ab - passend zum bestehenden Umgang mit
        Einzelfehlern beim NV-Polling (siehe reader.read_lookup()).
        """

        if self.poller is None:

            self.initialize()

        result = {}

        for schedule in self.schedules:

            try:

                result[schedule["oid"]] = self.client.get_object(
                    schedule["oid"]
                )

            except Exception as exc:

                _LOGGER.debug(
                    "Zeitprogramm-Abfrage fehlgeschlagen fuer %s: %s",
                    schedule["oid"],
                    exc,
                )

        return result

    def write_schedule(self, oid, blocks):
        """Ein Zeitprogramm (Schaltzeiten) schreiben.

        oid muss zu einem von discover_schedules() gefundenen
        Eintrag gehoeren - node_id/function_id/lookup/member werden
        daraus abgeleitet, nicht separat uebergeben.

        blocks: Liste von Schaltgruppen, je
        {"switch_points": [{"time": ..., "value": ...}, ...],
        "weekdays": [...]}. Windhager erlaubt mehrere Bloecke mit
        unterschiedlichen Wochentagen (z.B. ein Warmwasser-
        Zeitprogramm mit getrennten Werten fuer Mo-Sa und So) -
        verifiziert am 2026-07-28 per Browser-Devtools.
        """

        schedule = next(
            (
                entry
                for entry in self.schedules
                if entry["oid"] == oid
            ),
            None,
        )

        if schedule is None:

            raise ValueError(
                f"Unbekanntes Zeitprogramm-OID: {oid}"
            )

        self.client.write_object(
            node_id=schedule["module"].id,
            function_id=schedule["function_id"],
            oid_path=f"{schedule['lookup_id']}/{schedule['member_id']}",
            oid=oid,
            subtype_id=SCHEDULE_SUBTYPE_ID,
            type_id=SCHEDULE_TYPE_ID,
            value=[
                {
                    "switchPoints": block["switch_points"],
                    "weekdays": block["weekdays"],
                }
                for block in blocks
            ],
        )