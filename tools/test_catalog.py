from windhager_tools.catalog import load_catalog


def main():

    modules = load_catalog()

    print(f"{len(modules)} Module geladen.\n")

    for module in modules:

        print(f"[{module.id}] {module.name}")

        for function in module.functions:

            print(
                f"    [{function.id}] "
                f"{len(function.lookups)} Lookups"
            )

        print()


if __name__ == "__main__":
    main()