from pathlib import Path

from windhager_tools.catalog import (
    load_catalog,
    save_catalog,
)
from windhager_tools.crawler import crawl
from windhager_tools.poller import Poller


class WindhagerSystem:

    def __init__(self, client):

        self.client = client

        if Path("catalog.json").exists():

            print("Lade Katalog...")

            self.modules = load_catalog()

        else:

            print("Starte Discovery...")

            self.modules = crawl(client)

            save_catalog(self.modules)

        self.poller = Poller(
            client,
            self.modules
        )

    def poll(self):

        return self.poller.poll()