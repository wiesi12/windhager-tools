from collections import Counter
from pathlib import Path

from .catalog import (
    load_catalog,
    save_catalog,
)
from .crawler import crawl
from .poller import Poller


class WindhagerSystem:

    def __init__(
        self,
        client,
        catalog_path="catalog.json",
    ):

        self.client = client
        self.catalog_path = Path(catalog_path)

        self.modules = None
        self.poller = None

        self.oid_map = {}

    def initialize(self):

        if self.catalog_path.exists():

            print("Lade Katalog...")

            self.modules = load_catalog(
                self.catalog_path
            )

        else:

            print("Starte Discovery...")

            self.modules = crawl(
                self.client
            )

            save_catalog(
                self.modules,
                self.catalog_path,
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