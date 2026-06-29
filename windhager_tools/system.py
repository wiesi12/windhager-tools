from collections import Counter
import copy
from pathlib import Path

from windhager_tools.catalog import (
    load_catalog,
    save_catalog,
)
from windhager_tools.crawler import crawl
from windhager_tools.poller import Poller
from windhager_tools.resources import DEFAULT_LANGUAGE


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
    ):

        self.client = client
        self.catalog_path = Path(catalog_path)
        self.language = language

        # None bedeutet "alle Module"/"alle Gruppen"
        # (Rueckwaertskompatibilitaet fuer Config-Entries, die vor
        # Einfuehrung der Modul-/Gruppen-Auswahl eingerichtet wurden,
        # sowie fuer eigenstaendige Nutzung der Library ausserhalb der
        # HA-Integration).
        self.selected_module_ids = selected_module_ids
        self.selected_groups_by_module = (
            selected_groups_by_module
        )

        self.modules = None
        self.poller = None

        self.oid_map = {}

    def initialize(self):

        if self.catalog_path.exists():

            print("Lade Katalog...")

            all_modules = load_catalog(
                self.catalog_path
            )

        else:

            print("Starte Discovery...")

            all_modules = crawl(
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
            )

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

        self.poller = Poller(
            self.client,
            self.modules,
        )

        self.build_oid_map()

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