import re
import unicodedata


def slugify(text: str) -> str:

    text = unicodedata.normalize(
        "NFKD",
        text,
    ).encode(
        "ascii",
        "ignore",
    ).decode()

    text = text.lower()

    text = re.sub(
        r"[^a-z0-9]+",
        "_",
        text,
    )

    text = re.sub(
        r"_+",
        "_",
        text,
    )

    return text.strip("_")


def build_slug(
    module,
    lookup,
    entry,
) -> str:

    return "_".join(
        filter(
            None,
            (
                slugify(module.name),
                slugify(lookup.name),
                slugify(entry.name),
            ),
        )
    )