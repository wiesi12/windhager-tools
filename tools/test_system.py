from config import HOST, USER, PASSWORD

from windhager_tools.client import WindhagerClient
from windhager_tools.system import WindhagerSystem


def main():

    client = WindhagerClient(
        HOST,
        USER,
        PASSWORD
    )

    system = WindhagerSystem(client)

    values = system.poll()

    print()

    print(f"{len(values)} OIDs\n")

    for oid, entry in list(values.items())[:20]:

        print(
            f"{oid} = "
            f"{entry.value} "
            f"{entry.unit}"
        )


if __name__ == "__main__":
    main()