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

    def poll(self):

        if self.poller is None:

            self.initialize()

        return self.poller.poll()