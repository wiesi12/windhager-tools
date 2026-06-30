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


def save_catalog(modules, filename, enum_texts=None):
    """Katalog speichern.

    enum_texts ist optional (Rueckwaertskompatibilitaet fuer Aufrufer,
    die das Feature noch nicht nutzen) - ein Dict mit
    "{group}:{member}:{enum_value}" als String-Schluessel (JSON kennt
    keine Tupel als Objekt-Keys, daher hier als zusammengesetzter
    String statt als verschachtelte Struktur) auf den lesbaren Text.
    """

    filename = Path(filename)

    filename.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    data = {
        "modules": [
            asdict(module) for module in modules
        ],
        "enum_texts": {
            f"{group}:{member}:{enum_value}": text
            for (
                group,
                member,
                enum_value,
            ), text in (
                enum_texts or {}
            ).items()
        },
    }

    with filename.open(
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            data,
            f,
            indent=2,
            ensure_ascii=False,
        )


def load_catalog(filename):
    """Katalog laden.

    Liefert (modules, enum_texts) - enum_texts als Dict mit
    (group, member, enum_value)-Tupeln als Schluessel (wieder
    zurueckgewandelt aus dem JSON-kompatiblen String-Format, in dem
    save_catalog() sie ablegt).

    Rueckwaertskompatibel zum AELTEREN Katalog-Format (eine reine
    Liste von Modulen statt {"modules": [...], "enum_texts": {...}}):
    falls die geladenen Top-Level-Daten eine Liste sind statt eines
    Dicts, wird sie als "modules" interpretiert und enum_texts bleibt
    leer - so muessen Kataloge, die vor Einfuehrung dieses Features
    gespeichert wurden, nicht neu gecrawlt werden, nur weil sich das
    Format geaendert hat.
    """

    filename = Path(filename)

    with filename.open(
        "r",
        encoding="utf-8",
    ) as f:

        raw = json.load(f)

    if isinstance(raw, list):

        module_list_data = raw
        enum_texts_data = {}

    else:

        module_list_data = raw["modules"]
        enum_texts_data = raw.get(
            "enum_texts",
            {},
        )

    enum_texts = {}

    for key, text in enum_texts_data.items():

        group_str, member_str, enum_value_str = (
            key.split(":")
        )

        enum_texts[
            (
                int(group_str),
                int(member_str),
                int(enum_value_str),
            )
        ] = text

    modules = []

    for module_data in module_list_data:

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
                            unit=entry_data.get("unit"),
                            unit_id=entry_data.get("unit_id"),

                            type_id=entry_data.get("type_id"),
                            subtype_id=entry_data.get("subtype_id"),

                            write_protected=entry_data["write_protected"],

                            group=entry_data.get("group"),
                            member=entry_data.get("member"),

                            min_value=entry_data.get("min_value"),
                            max_value=entry_data.get("max_value"),

                            step=entry_data.get("step"),
                            step_id=entry_data.get("step_id"),

                            timestamp=entry_data.get("timestamp"),

                            name=entry_data.get("name", ""),
                        )

                    else:

                        entry = NvEntry(
                            index=entry_data["index"],
                            name=entry_data["name"],
                            snvt_name=entry_data.get("snvt_name"),
                            snvt_index=entry_data.get("snvt_index"),
                            value=entry_data.get("value"),
                            unit=entry_data.get("unit"),
                        )

                    lookup.entries.append(entry)

                function.lookups.append(lookup)

            module.functions.append(function)

        modules.append(module)

    return modules, enum_texts