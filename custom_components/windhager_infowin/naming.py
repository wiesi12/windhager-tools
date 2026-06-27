from . import nv_names


def build_entity_name(entry, lookup):

    # NvEntry (LON-Netzwerkvariablen) haben kein oid-Attribut und
    # eine eigene, lesbare Namens-Zuordnung statt der Lookup/Entry-
    # Kombinationslogik unten, da ihr lookup.name immer nur "NV's"
    # ist und damit keine sinnvolle Gruppierung liefert.
    if not hasattr(entry, "oid"):

        return nv_names.readable_nv_name(
            entry.name
        )

    lookup_name = (lookup.name or "").strip()
    entry_name = (entry.name or "").strip()

    if not lookup_name:
        return entry_name or f"Member {entry.member}"

    if not entry_name:
        return lookup_name

    # Doppelten Namen vermeiden
    if entry_name.casefold() == lookup_name.casefold():
        return entry_name

    # "Raumtemperatur" + "Aktuelle Raumtemperatur"
    if entry_name.casefold().startswith(lookup_name.casefold()):
        return entry_name

    # "Kesseltemperatur Solltemperatur"
    if entry_name.casefold().startswith("soll"):
        return f"{lookup_name} {entry_name}"

    if entry_name.casefold().startswith("ist"):
        return f"{lookup_name} {entry_name}"

    # Gruppen, deren Name nur als Container dient
    if lookup_name in {
        "Auslegungstemperaturen",
        "Zeitschaltprogramm",
        "Zeitprogramm",
    }:
        return entry_name

    return f"{lookup_name} {entry_name}"