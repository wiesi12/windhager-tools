from homeassistant.core import HomeAssistant

from .lib.resources import (
    DEFAULT_LANGUAGE,
    SUPPORTED_LANGUAGES,
)


def resolve_language(hass: HomeAssistant) -> str:
    """HA-Systemsprache (z.B. "de", "en-GB") auf eine der von
    Windhager unterstuetzten Sprachen abbilden.

    hass.config.language folgt BCP47 (kann also Regionscodes wie
    "en-GB" enthalten) - hier wird nur der fuehrende Sprachteil
    verglichen. Nicht unterstuetzte Sprachen (z.B. "nl") fallen auf
    Deutsch zurueck, da das die einzige garantiert vorhandene
    Ressourcendatei auf der Windhager-Box ist.

    Gemeinsam genutzt von __init__.py (eigentliches Setup) und
    config_flow.py (Struktur-Discovery waehrend der Einrichtung), um
    Code-Duplikation zu vermeiden.
    """

    raw_language = (
        hass.config.language or DEFAULT_LANGUAGE
    )

    base_language = raw_language.split("-")[0].lower()

    if base_language in SUPPORTED_LANGUAGES:
        return base_language

    return DEFAULT_LANGUAGE
