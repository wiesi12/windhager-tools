from config import HOST, USER, PASSWORD

from windhager_tools.catalog import load_catalog
from windhager_tools.client import WindhagerClient
from windhager_tools.poller import Poller


def main():

    client = WindhagerClient(
        HOST,
        USER,
        PASSWORD
    )

    print("Verbunden.\n")

    modules = load_catalog()

    poller = Poller(
        client,
        modules
    )

    entries = poller.poll()

    print(f"{len(entries)} Einträge gefunden.\n")

    for entry in entries[:20]:

        if hasattr(entry, "oid"):

            print(
                f"{entry.oid} = "
                f"{entry.value} {entry.unit}"
            )

        else:

            print(
                f"{entry.name} = "
                f"{entry.value} {entry.unit}"
            )


if __name__ == "__main__":
    main()