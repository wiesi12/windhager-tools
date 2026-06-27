from collections import Counter

from windhager_tools.catalog import load_catalog


def main():

    print("Lade Katalog...\n")

    modules = load_catalog("catalog.json")

    triples = []

    for module in modules:

        for function in module.functions:

            for lookup in function.lookups:

                for entry in lookup.entries:

                    triples.append(
                        (
                            module.name,
                            lookup.name,
                            entry.name,
                        )
                    )

    triples.sort()

    print("=== MODULE | LOOKUP | ENTRY ===\n")

    for module, lookup, entry in triples:

        print(
            f"{module} | {lookup} | {entry}"
        )

    print("\n=== DUPLICATE ENTRY NAMES ===\n")

    counts = Counter(
        entry
        for _, _, entry in triples
    )

    duplicates = [
        (name, count)
        for name, count in counts.items()
        if count > 1
    ]

    duplicates.sort(
        key=lambda x: (-x[1], x[0])
    )

    for name, count in duplicates:

        print(
            f"{count:>3} × {name}"
        )


if __name__ == "__main__":
    main()