from config import HOST, USER, PASSWORD
from windhager_tools.catalog import save_catalog
from windhager_tools.client import WindhagerClient
from windhager_tools.crawler import crawl
from windhager_tools.reader import read_lookup


def main():

    client = WindhagerClient(
        HOST,
        USER,
        PASSWORD
    )

    print("Verbunden.\n")

    modules = crawl(client)
    save_catalog(modules)
    for module in modules:

        print(f"[{module.id}] {module.name}")

        for function in module.functions:

            print(f"    [{function.id}] {function.name}")

            for lookup in function.lookups:

                print(f"        [{lookup.id}]")

                for entry in lookup.entries:

                    if hasattr(entry, "oid"):

                        print(
                            f"            {entry.oid} = "
                            f"{entry.value} {entry.unit}"
                        )

                    else:

                        print(
                            f"            {entry.name} = "
                            f"{entry.value} {entry.unit}"
                        )

        print()

if __name__ == "__main__":
    main()