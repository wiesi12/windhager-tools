import json
from dataclasses import asdict
from pathlib import Path

from .models import (
    Module,
    Function,
    Lookup,
    Entry,
    NvEntry,
)


def save_catalog(modules, filename):

    filename = Path(filename)

    filename.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with filename.open(
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            [asdict(module) for module in modules],
            f,
            indent=2,
            ensure_ascii=False,
        )


def load_catalog(filename):

    filename = Path(filename)

    with filename.open(
        "r",
        encoding="utf-8",
    ) as f:

        data = json.load(f)

    modules = []

    for module_data in data:

        module = Module(
            id=module_data["id"],
            name=module_data["name"],
            group=module_data["group"],
            subnet=module_data["subnet"],
            program_id=module_data["program_id"],
            neuron_id=module_data["neuron_id"],
        )

        for function_data in module_data["functions"]:

            function = Function(
                id=function_data["id"],
                type=function_data["type"],
                name=function_data["name"],
                locked=function_data["locked"],
            )

            for lookup_data in function_data["lookups"]:

                lookup = Lookup(
                    id=lookup_data["id"],
                    count=lookup_data["count"],
                    name=lookup_data.get(
                        "name",
                        "",
                    ),
                )

                for entry_data in lookup_data["entries"]:

                    if "oid" in entry_data:

                        entry = Entry(
                            oid=entry_data["oid"],
                            value=entry_data["value"],
                            unit=entry_data["unit"],
                            type_id=entry_data["type_id"],
                            write_protected=entry_data["write_protected"],
                            group=entry_data.get("group"),
                            member=entry_data.get("member"),
                            name=entry_data.get("name", ""),
                        )

                    else:

                        entry = NvEntry(
                            index=entry_data["index"],
                            name=entry_data["name"],
                            snvt_name=entry_data["snvt_name"],
                            snvt_index=entry_data["snvt_index"],
                            value=entry_data["value"],
                            unit=entry_data["unit"],
                        )

                    lookup.entries.append(entry)

                function.lookups.append(lookup)

            module.functions.append(function)

        modules.append(module)

    return modules