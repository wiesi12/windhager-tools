from . import nv_names
from .const import DOMAIN


def via_device(system, module):
    """Device-Identifier-Tupel fuer via_device liefern, falls fuer
    dieses Modul eine Geraete-Hierarchie konfiguriert ist - sonst
    None (flache Struktur, Standardverhalten).

    system.boiler_module_id wird vom Nutzer im Options Flow gewaehlt
    (siehe config_flow.py::async_step_select_boiler) - es gibt
    bewusst KEINE automatische Erkennung, da sich "das ist der
    Waermeerzeuger" nicht zuverlaessig aus den Modul-Metadaten
    ableiten laesst (manche Waermeerzeuger wie BioWIN haben keinen
    aussagekraeftigen eigenen Funktionstyp).
    """

    boiler_module_id = getattr(
        system,
        "boiler_module_id",
        None,
    )

    if boiler_module_id is None:
        return None

    if module.id == boiler_module_id:
        # Das Waermeerzeuger-Geraet selbst braucht kein via_device
        # auf sich selbst.
        return None

    return (
        DOMAIN,
        f"module2_{boiler_module_id}",
    )


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