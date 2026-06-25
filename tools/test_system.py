from config import HOST, USER, PASSWORD

from windhager.client import WindhagerClient
from windhager.system import WindhagerSystem


def main():

    client = WindhagerClient(
        HOST,
        USER,
        PASSWORD
    )

    system = WindhagerSystem(client)

    entries = system.poll()

    print()

    print(f"{len(entries)} Einträge")

    for entry in entries[:20]:

        if hasattr(entry, "oid"):

            print(
                f"{entry.oid} = "
                f"{entry.value} {entry.unit}"
            )


if __name__ == "__main__":
    main()