import logging
import time
from pathlib import Path

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .lib import (
    WindhagerClient,
    WindhagerSystem,
)

from . import metadata
from .const import DOMAIN
from .coordinator import (
    WindhagerCoordinator,
    WindhagerNvCoordinator,
)
from .language import resolve_language


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

    language = resolve_language(hass)

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

        # .get() statt direktem Zugriff: Config-Entries, die VOR
        # Einfuehrung der Modul-/Gruppen-Auswahl eingerichtet wurden,
        # haben diese Felder noch nicht - None bedeutet fuer
        # WindhagerSystem "alle Module"/"alle Gruppen verwenden"
        # (Ruckwaertskompatibilitaet).
        selected_module_ids = entry.data.get(
            "selected_modules"
        )

        selected_groups_by_module = entry.data.get(
            "selected_groups"
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
            selected_module_ids=selected_module_ids,
            selected_groups_by_module=selected_groups_by_module,
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
            _refresh_then_reconcile(
                hass,
                entry,
                system,
                nv_coordinator,
            ),
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

    if not existing_nv_entities:

        # NUR im blockierenden Pfad hier direkt aufrufen - im
        # Hintergrund-Pfad uebernimmt das bereits
        # _refresh_then_reconcile() oben, NACHDEM der Hintergrund-
        # Refresh tatsaechlich fertig ist (siehe dort fuer die
        # Begruendung, warum ein direkter Aufruf hier im
        # Hintergrund-Fall eine Race Condition waere).
        await _reconcile_entity_categories(
            hass,
            entry,
            system,
            nv_coordinator,
        )

    _LOGGER.debug(
        "Setup abgeschlossen in %.1fs insgesamt",
        time.monotonic() - setup_started_at,
    )

    return True


async def _refresh_then_reconcile(
    hass: HomeAssistant,
    entry: ConfigEntry,
    system: WindhagerSystem,
    nv_coordinator: WindhagerNvCoordinator,
) -> None:
    """Hintergrund-Task-Helfer: erst den NV-Refresh ABWARTEN, dann
    erst _reconcile_entity_categories() aufrufen.

    WICHTIG: existiert als eigene Funktion, damit beide Schritte
    INNERHALB desselben Hintergrund-Tasks sequentiell laufen. Ein
    direkter Aufruf von _reconcile_entity_categories() im normalen
    async_setup_entry()-Ablauf (parallel zum per
    entry.async_create_background_task() gestarteten Refresh) waere
    eine Race Condition: nv_coordinator.data waere zu diesem
    Zeitpunkt noch leer/veraltet, wodurch is_raw_hex_value() auf dem
    statischen Katalog-Platzhalter ("-") statt dem echten Live-Wert
    rechnen wuerde - also fast immer faelschlich "kein Hex-Wert".
    """

    await nv_coordinator.async_refresh()

    await _reconcile_entity_categories(
        hass,
        entry,
        system,
        nv_coordinator,
    )


async def _reconcile_entity_categories(
    hass: HomeAssistant,
    entry: ConfigEntry,
    system: WindhagerSystem,
    nv_coordinator: WindhagerNvCoordinator,
) -> None:
    """Die entity_category bestehender Sensoren mit dem aktuell
    korrekten Wert abgleichen, statt sich auf das HA-Standard-
    verhalten zu verlassen.

    HA wertet entity_category (genauso wie suggested_object_id/name)
    NUR beim ALLERERSTEN Hinzufuegen einer Entity zur Registry aus -
    bei einem regulaeren Update/Neustart mit bereits existierender
    unique_id behaelt eine Entity ihren alten, in der Registry
    gespeicherten Wert bei, selbst wenn ein Integrations-Update die
    zugrundeliegende Klassifizierungslogik (z.B.
    metadata.is_raw_hex_value()) verbessert hat.

    Das betrifft nicht nur Entwickler-Workflows: ein normales HACS-
    Update (neue Dateien + Neustart, OHNE die Integration manuell neu
    einzurichten) faellt genau in dieses Muster. Ohne diesen Abgleich
    wuerden z.B. neu erkannte Hex-Bitfeld-Sensoren erst nach einem
    manuellen Entfernen+Neueinrichten der Integration korrekt als
    Diagnose-Entity einsortiert, was die meisten Nutzer nicht erwarten.

    Schreibt die Registry NUR bei tatsaechlicher Abweichung (nicht bei
    jedem Start blind alle Entities neu setzen) - HA raet explizit zu
    Zurueckhaltung bei haeufigen entity_category-Aenderungen.
    """

    registry = er.async_get(hass)

    nv_data = nv_coordinator.data or {}

    updated_count = 0

    for entity_entry in er.async_entries_for_config_entry(
        registry,
        entry.entry_id,
    ):

        unique_id = (
            getattr(
                entity_entry,
                "unique_id",
                "",
            )
            or ""
        )

        if not unique_id.startswith("windhager_v2_"):

            # Sollte bei dieser Integration nie vorkommen (nur sie
            # selbst registriert Entities mit diesem Domain), aber
            # sicherheitshalber keine fremden Entities anfassen.
            continue

        oid = unique_id[
            len("windhager_v2_"):
        ]

        info = system.oid_map.get(oid)

        if info is None:
            continue

        # Fuer NV's den aktuellen Wert aus dem NV-Coordinator nehmen
        # (falls schon vorhanden), sonst auf den statischen Katalog-
        # Wert zurueckfallen - dasselbe Muster wie sensor.py's
        # live_entry-Property.
        live_entry = nv_data.get(oid)

        live_value = (
            live_entry.value
            if live_entry is not None
            else info["entry"].value
        )

        correct_category = metadata.entity_category(
            info["lookup"],
            info["entry"],
            live_value,
        )

        if entity_entry.entity_category != correct_category:

            registry.async_update_entity(
                entity_entry.entity_id,
                entity_category=correct_category,
            )

            updated_count += 1

    if updated_count:

        _LOGGER.info(
            "entity_category fuer %d bestehende Sensoren "
            "korrigiert (Klassifizierungslogik hat sich seit "
            "deren erster Registrierung geaendert)",
            updated_count,
        )


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