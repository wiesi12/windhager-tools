import json
from dataclasses import asdict


def save_catalog(modules, filename="catalog.json"):

    with open(filename, "w", encoding="utf-8") as f:

        json.dump(
            [asdict(module) for module in modules],
            f,
            indent=2,
            ensure_ascii=False
        )