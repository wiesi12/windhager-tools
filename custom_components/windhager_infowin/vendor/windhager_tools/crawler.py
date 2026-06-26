from .discovery import (
    discover_modules,
    discover_functions,
    discover_lookups,
)
from .reader import read_lookup
from .resources import (
    ResourceDatabase,
)


def crawl(client):

    resources = ResourceDatabase()

    resources.load(client)

    modules = discover_modules(client)

    for module in modules:

        discover_functions(client, module)

        for function in module.functions:

            discover_lookups(
                client,
                module,
                function,
            )

            for lookup in function.lookups:

                lookup.name = resources.level_name(
                    function.type,
                    lookup.id,
                ) or ""

                lookup.entries = read_lookup(
                    client,
                    module,
                    function,
                    lookup,
                )

                for entry in lookup.entries:

                    if hasattr(entry, "group"):

                        entry.name = resources.variable_name(
                            entry.group,
                            entry.member,
                        ) or ""

    return modules