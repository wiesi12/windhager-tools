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

    # NvEntry (LON-Netzwerkvariablen) haben kein oid/member-Attribut
    # und lookup.name ist bei ihnen immer nur "NV's" (keine sinnvolle
    # Gruppierung). Stattdessen wird der technische NV-Name verwendet,
    # ergaenzt um den pro-Modul eindeutigen index als Disambiguierer
    # (z.B. falls zwei NV-Variablen denselben Basisnamen teilen).
    if not hasattr(entry, "oid"):

        return "_".join(
            filter(
                None,
                (
                    slugify(entry.name),
                    str(entry.index),
                ),
            )
        )

    # Fallback fuer Entries ohne eigenen Namen (analog zu naming.py:
    # "Member {member}"), damit auch in diesem Fall ein stabiler,
    # nicht-leerer Object-ID-Bestandteil entsteht.
    entry_part = entry.name

    if not (entry_part or "").strip():

        if entry.member is not None:
            entry_part = f"member_{entry.member}"
        else:
            entry_part = entry.oid

    # module.name wird bewusst NICHT mit eingeschlossen: Home Assistant
    # stellt bei has_entity_name=True ohnehin automatisch Area- und
    # Geraete-Namen (= module.name) vor den hier zurueckgegebenen Object-Id-
    # Teil. Wuerde module.name hier zusaetzlich eingebaut, entstuende eine
    # Dopplung wie "controlroom_hk1_og1_2_hk1_og1_2_...".
    return "_".join(
        filter(
            None,
            (
                slugify(lookup.name),
                slugify(entry_part),
            ),
        )
    )