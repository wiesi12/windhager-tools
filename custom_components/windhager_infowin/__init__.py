from pathlib import Path

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .vendor.windhager_tools import (
    WindhagerClient,
    WindhagerSystem,
)
from .vendor.windhager_tools.resources import (
    DEFAULT_LANGUAGE,
    SUPPORTED_LANGUAGES,
)

from .const import DOMAIN
from .coordinator import (
    WindhagerCoordinator,
    WindhagerNvCoordinator,
)


# Unterordner INNERHALB der Integration selbst (nicht im HA-Config-
# Root) fuer den zwischengespeicherten Discovery-Katalog. Der Vorteil
# gegenueber hass.config.path(): wird der gesamte Integrations-Ordner
# entfernt (z.B. durch HACS-Deinstallation), verschwindet der Katalog
# automatisch mit - es bleiben keine verwaisten Dateien im HA-Config-
# Verzeichnis zurueck. In hacs.json als "persistent_directory"
# deklariert, damit HACS diesen Ordner bei Updates nicht versehentlich
# loescht/ueberschreibt.
DATA_DIR = Path(__file__).parent / "data"


def _resolve_language(hass: HomeAssistant) -> str:
    """HA-Systemsprache (z.B. "de", "en-GB") auf eine der von
    Windhager unterstuetzten Sprachen abbilden.

    hass.config.language folgt BCP47 (kann also Regionscodes wie
    "en-GB" enthalten) - hier wird nur der fuehrende Sprachteil
    verglichen. Nicht unterstuetzte Sprachen (z.B. "nl") fallen auf
    Deutsch zurueck, da das die einzige garantiert vorhandene
    Ressourcendatei auf der Windhager-Box ist.
    """

    raw_language = (
        hass.config.language or DEFAULT_LANGUAGE
    )

    base_language = raw_language.split("-")[0].lower()

    if base_language in SUPPORTED_LANGUAGES:
        return base_language

    return DEFAULT_LANGUAGE


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> bool:

    client = WindhagerClient(
        entry.data["host"],
        entry.data["username"],
        entry.data["password"],
    )

    language = _resolve_language(hass)

    def _build_system():

        # DATA_DIR.mkdir() ist blockierendes Dateisystem-I/O und
        # gehoert daher in den executor job, nicht in den Event-Loop.
        DATA_DIR.mkdir(
            parents=True,
            exist_ok=True,
        )

        return WindhagerSystem(
            client,
            # Sprache im Dateinamen, damit ein spaeterer Wechsel der
            # HA-Systemsprache automatisch einen frischen Discovery-
            # Crawl in der neuen Sprache ausloest, statt den alten
            # Katalog der vorherigen Sprache weiterzuverwenden.
            str(
                DATA_DIR
                / f"catalog_{language}.json"
            ),
            language=language,
        )

    system = await hass.async_add_executor_job(
        _build_system
    )

    await hass.async_add_executor_job(
        system.initialize
    )

    coordinator = WindhagerCoordinator(
        hass,
        entry,
        system,
    )

    await coordinator.async_config_entry_first_refresh()

    nv_coordinator = WindhagerNvCoordinator(
        hass,
        entry,
        system,
    )

    # WICHTIG: bewusst BLOCKIEREND (anders als zuvor). Ein nicht-
    # blockierender Hintergrund-Refresh fuehrte zu einer Race
    # Condition: einige Eigenschaften (z.B. entity_category, siehe
    # metadata.is_raw_hex_value()) werden von Home Assistant NUR beim
    # allerersten Hinzufuegen der Entity zur Registry ausgewertet -
    # zu diesem Zeitpunkt lag bei nicht-blockierendem Refresh aber nur
    # der Platzhalterwert "-" vor, wodurch z.B. rohe Hex-Bitfeld-Werte
    # faelschlich NICHT als Diagnose-Entity erkannt wurden. Kostet
    # zusaetzliche Sekunden beim Einrichten/Neuladen der Integration,
    # garantiert dafuer korrekte Metadaten ab dem ersten Start.
    await nv_coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})

    hass.data[DOMAIN][entry.entry_id] = {
        "system": system,
        "coordinator": coordinator,
        "nv_coordinator": nv_coordinator,
    }

    await hass.config_entries.async_forward_entry_setups(
        entry,
        ["sensor"],
    )

    return True


async def async_unload_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> bool:

    unload_ok = await hass.config_entries.async_unload_platforms(
        entry,
        ["sensor"],
    )

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok