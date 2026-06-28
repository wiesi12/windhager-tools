from .discovery import (
    discover_modules,
    discover_functions,
    discover_lookups,
)
from .reader import read_lookup
from .resources import (
    DEFAULT_LANGUAGE,
    Resources,
)


def crawl(client, language=DEFAULT_LANGUAGE):

    resources = Resources(language)

    resources.load(client)

    modules = discover_modules(client)

    for module in modules:

        discover_functions(
            client,
            module,
        )

        for function in module.functions:

            discover_lookups(
                client,
                module,
                function,
            )

            for lookup in function.lookups:

                lookup.name = (
                    resources.lookup_name(
                        lookup.id,
                    )
                    or ""
                )

                lookup.entries = read_lookup(
                    client,
                    module,
                    function,
                    lookup,
                )

                for entry in lookup.entries:

                    if hasattr(
                        entry,
                        "group",
                    ):

                        entry.name = (
                            resources.entry_name(
                                entry.group,
                                entry.member,
                            )
                            or ""
                        )

    return modules