from config import HOST, USER, PASSWORD

from windhager.client import WindhagerClient
from windhager.crawler import crawl
from windhager.poller import Poller


def main():

    client = WindhagerClient(
        HOST,
        USER,
        PASSWORD
    )

    print("Verbunden.\n")

    modules = crawl(client)

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