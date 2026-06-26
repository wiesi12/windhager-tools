from pathlib import Path

from windhager_tools.catalog import (
    load_catalog,
    save_catalog,
)
from windhager_tools.crawler import crawl
from windhager_tools.poller import Poller


class WindhagerSystem:

    def __init__(
        self,
        client,
        catalog_path="catalog.json",
    ):

        self.client = client
        self.catalog_path = Path(catalog_path)

        if self.catalog_path.exists():

            print("Lade Katalog...")

            self.modules = load_catalog(
                self.catalog_path
            )

        else:

            print("Starte Discovery...")

            self.modules = crawl(client)

            save_catalog(
                self.modules,
                self.catalog_path,
            )

        self.poller = Poller(
            client,
            self.modules,
        )

    def poll(self):

        return self.poller.poll()