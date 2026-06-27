from collections import Counter, defaultdict

from config import HOST, USER, PASSWORD

from windhager_tools.client import WindhagerClient
from windhager_tools.system import WindhagerSystem


def main():

    client = WindhagerClient(
        HOST,
        USER,
        PASSWORD,
    )

    system = WindhagerSystem(client)

    system.initialize()

    type_counter = Counter()
    unit_counter = Counter()

    type_examples = defaultdict(list)

    for module in system.modules:

        for function in module.functions:

            for lookup in function.lookups:

                for entry in lookup.entries:

                    if not hasattr(entry, "oid"):
                        continue

                    type_counter[entry.type_id] += 1
                    unit_counter[entry.unit] += 1

                    key = (
                        entry.type_id,
                        entry.unit,
                    )

                    if len(type_examples[key]) < 5:

                        type_examples[key].append(
                            entry.value
                        )

    print("\n=== TYPE IDs ===\n")

    for type_id in sorted(type_counter):

        print(
            f"{type_id:>3} : "
            f"{type_counter[type_id]}"
        )

    print("\n=== UNITS ===\n")

    for unit in sorted(
        unit_counter,
        key=lambda x: "" if x is None else str(x),
    ):

        label = "None" if unit is None else unit

        print(
            f"{label:>8} : "
            f"{unit_counter[unit]}"
        )

    print("\n=== TYPE DETAILS ===\n")

    for key in sorted(
        type_examples,
        key=lambda x: (
            x[0],
            "" if x[1] is None else str(x[1]),
        ),
    ):

        type_id, unit = key

        print(
            f"TYPE {type_id} | UNIT {unit}"
        )

        for value in type_examples[key]:

            print(f"    {value}")

        print()


if __name__ == "__main__":
    main()