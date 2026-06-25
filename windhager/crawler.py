from windhager.discovery import (
    discover_modules,
    discover_functions,
    discover_lookups,
)
from windhager.reader import read_lookup


def crawl(client):

    modules = discover_modules(client)

    for module in modules:

        discover_functions(client, module)

        for function in module.functions:

            discover_lookups(client, module, function)

            for lookup in function.lookups:

                lookup.entries = read_lookup(
                    client,
                    module,
                    function,
                    lookup
                )

    return modules