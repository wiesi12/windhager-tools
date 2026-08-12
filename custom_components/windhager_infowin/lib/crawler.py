import logging

import requests

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

_LOGGER = logging.getLogger(__name__)


def crawl_structure(client, language=DEFAULT_LANGUAGE):
    """Nur die STRUKTUR der Anlage ermitteln (Module, Functions,
    Lookup-Gruppen samt Namen) - OHNE die eigentlichen Werte pro
    Lookup-Gruppe abzufragen (read_lookup()).

    Fuer eine Anlage wie die hier referenzierte (5 Module) ergibt das
    ca. 1 + 5 + (Anzahl Functions ueber alle Module) API-Calls - eine
    Grossenordnung weniger als der volle crawl() (der zusaetzlich
    einen Call PRO Lookup-Gruppe braucht, bei dieser Anlage rund 80).

    Gedacht fuer den Config-Flow: dort wird nur die Struktur benoetigt,
    um dem Nutzer eine Modul-/Lookup-Gruppen-Auswahl anzuzeigen, bevor
    der eigentliche (teure) Daten-Crawl bei der Einrichtung laeuft.
    """

    resources = Resources(language)

    resources.load(client)

    modules = discover_modules(client)

    for module in modules:

        discover_functions(
            client,
            module,
        )

        for function in module.functions:

            try:
                discover_lookups(
                    client,
                    module,
                    function,
                )
            except (requests.HTTPError, requests.exceptions.Timeout, requests.exceptions.ConnectionError) as exc:
                _LOGGER.debug(
                    "Skipping lookups for module %s function %s: %s",
                    module.id,
                    function.id,
                    exc,
                )
                function.lookups = []
                continue

            for lookup in function.lookups:

                lookup.name = (
                    resources.lookup_name(
                        function.type,
                        lookup.id,
                    )
                    or ""
                )

    return modules


def crawl(client, language=DEFAULT_LANGUAGE):
    """Vollstaendigen Katalog ermitteln (Struktur + Werte + Namen).

    Liefert (modules, enum_texts) - enum_texts ist die KOMPLETTE
    AufzaehlTexte-Tabelle (nicht nur die fuer tatsaechlich gefundene
    Enum-Eintraege relevanten Teile), damit sie unveraendert in
    catalog.save_catalog() uebernommen werden kann.
    """

    resources = Resources(language)

    resources.load(client)

    modules = discover_modules(client)

    for module in modules:

        discover_functions(
            client,
            module,
        )

        for function in module.functions:

            try:
                discover_lookups(
                    client,
                    module,
                    function,
                )
            except (requests.HTTPError, requests.exceptions.Timeout, requests.exceptions.ConnectionError) as exc:
                _LOGGER.debug(
                    "Skipping lookups for module %s function %s: %s",
                    module.id,
                    function.id,
                    exc,
                )
                function.lookups = []
                continue

            for lookup in function.lookups:

                lookup.name = (
                    resources.lookup_name(
                        function.type,
                        lookup.id,
                    )
                    or ""
                )

                try:
                    lookup.entries = read_lookup(
                        client,
                        module,
                        function,
                        lookup,
                    )
                except (requests.HTTPError, requests.exceptions.Timeout, requests.exceptions.ConnectionError) as exc:
                    _LOGGER.debug(
                        "Skipping entries for module %s function %s lookup %s: %s",
                        module.id,
                        function.id,
                        lookup.id,
                        exc,
                    )
                    lookup.entries = []
                    continue

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

    return modules, resources.enum_texts