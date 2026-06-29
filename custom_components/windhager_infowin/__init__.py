import logging
import time
from pathlib import Path

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

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


_LOGGER = logging.getLogger(__name__)


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

    setup_started_at = time.monotonic()

    _LOGGER.debug(
        "Setup gestartet fuer %s",
        entry.data.get("host"),
    )

    client = WindhagerClient(
        entry.data["host"],
        entry.data["username"],
        entry.data["password"],
    )

    language = _resolve_language(hass)

    _LOGGER.debug(
        "Sprache aufgeloest: %s",
        language,
    )

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

    catalog_existed_before = await hass.async_add_executor_job(
        system.catalog_path.exists
    )

    initialize_started_at = time.monotonic()

    await hass.async_add_executor_job(
        system.initialize
    )

    initialize_duration = (
        time.monotonic() - initialize_started_at
    )

    if catalog_existed_before:

        _LOGGER.debug(
            "Katalog aus Cache geladen (%s) in %.1fs",
            system.catalog_path,
            initialize_duration,
        )

    else:

        _LOGGER.info(
            "Neuer Discovery-Crawl abgeschlossen in %.1fs "
            "(Katalog gespeichert unter %s)",
            initialize_duration,
            system.catalog_path,
        )

    coordinator = WindhagerCoordinator(
        hass,
        entry,
        system,
    )

    coordinator_refresh_started_at = time.monotonic()

    await coordinator.async_config_entry_first_refresh()

    _LOGGER.debug(
        "Erster Sensor-Refresh abgeschlossen in %.1fs",
        time.monotonic() - coordinator_refresh_started_at,
    )

    nv_coordinator = WindhagerNvCoordinator(
        hass,
        entry,
        system,
    )

    # Nur beim ALLERERSTEN Setup dieser Config-Entry blockierend
    # warten - erkennbar daran, dass noch kein einziger NV-Sensor in
    # der Entity-Registry existiert. Grund: einige Eigenschaften
    # (z.B. entity_category, siehe metadata.is_raw_hex_value()) werden
    # von Home Assistant NUR beim allerersten Hinzufuegen einer Entity
    # zur Registry ausgewertet - ein nicht-blockierender Hintergrund-
    # Refresh wuerde zu diesem Zeitpunkt nur den Platzhalterwert "-"
    # liefern, wodurch z.B. rohe Hex-Bitfeld-Werte faelschlich NICHT
    # als Diagnose-Entity erkannt wuerden.
    #
    # Bei jedem WEITEREN Start (normaler HA-Neustart, Reload) sind
    # diese einmalig ausgewerteten Eigenschaften bereits korrekt in
    # der Registry gespeichert - hier lohnt sich das Warten nicht
    # mehr und wuerde nur unnoetig ~200 zusaetzliche, sequentielle
    # API-Calls in die kritische Startphase zwingen.
    registry = er.async_get(hass)

    existing_nv_entities = [
        entry_
        for entry_ in er.async_entries_for_config_entry(
            registry,
            entry.entry_id,
        )
        if (
            getattr(entry_, "unique_id", "") or ""
        ).startswith("windhager_v2_nv:")
    ]

    if existing_nv_entities:

        _LOGGER.debug(
            "%d bestehende NV-Entities gefunden - "
            "NV-Refresh laeuft im Hintergrund",
            len(existing_nv_entities),
        )

        entry.async_create_background_task(
            hass,
            nv_coordinator.async_refresh(),
            name=f"{DOMAIN}_nv_first_refresh",
        )

    else:

        _LOGGER.info(
            "Keine bestehenden NV-Entities gefunden - "
            "warte blockierend auf ersten NV-Refresh "
            "(kann je nach Anlagengroesse 30-90s dauern)",
        )

        nv_refresh_started_at = time.monotonic()

        await nv_coordinator.async_config_entry_first_refresh()

        _LOGGER.info(
            "Erster NV-Refresh abgeschlossen in %.1fs",
            time.monotonic() - nv_refresh_started_at,
        )

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

    _LOGGER.debug(
        "Setup abgeschlossen in %.1fs insgesamt",
        time.monotonic() - setup_started_at,
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