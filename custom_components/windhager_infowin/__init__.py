import logging
import time
from pathlib import Path

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from .lib import (
    WindhagerClient,
    WindhagerSystem,
)

from . import metadata
from .const import DATA_DIR, DOMAIN
from .coordinator import (
    WindhagerCoordinator,
    WindhagerNvCoordinator,
)
from .language import resolve_language


_LOGGER = logging.getLogger(__name__)


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

    # Erst alte/veraltete Entities und Geraete bereinigen, BEVOR die
    # Plattformen (sensor/number/select) ihre Entities anlegen.
    # WICHTIG: Diese Reihenfolge ist entscheidend - wuerde
    # async_forward_entry_setups() zuerst laufen, wuerde HA versuchen
    # neue Entities (z.B. select.*) anzulegen, scheitert aber weil
    # die alten Entries (z.B. sensor.*) mit derselben unique_id noch
    # in der Registry sind. HA's unique_id ist global eindeutig, auch
    # ueber Domains hinweg - der alte Eintrag muss also ZUERST
    # entfernt werden, bevor der neue angelegt werden kann.
    await _reconcile_devices(
        hass,
        entry,
        system,
    )

    await _reconcile_entities(
        hass,
        entry,
        system,
    )

    await hass.config_entries.async_forward_entry_setups(
        entry,
        ["sensor", "number", "select"],
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


async def _reconcile_devices(
    hass: HomeAssistant,
    entry: ConfigEntry,
    system: WindhagerSystem,
) -> None:
    """Geraete entfernen, die zu einem FRUEHEREN Zeitpunkt erstellt
    wurden (z.B. ein Modul, das frueher ausgewaehlt war), aber bei der
    AKTUELLEN Modul-Auswahl (system.modules, nach Filterung durch
    selected_modules) nicht mehr vorkommen.

    Anders als bei entity_category (siehe _reconcile_entity_categories)
    geht es hier nicht um eine sich AENDERNDE Klassifizierungslogik,
    sondern um ein in Home-Assistant generell bekanntes Muster: wenn
    eine Integration bei einem Setup-Durchlauf bestimmte Geraete nicht
    mehr erzeugt, werden ihre vorher angelegten Eintraege NICHT
    automatisch aus der Device-Registry entfernt - das muss die
    Integration aktiv selbst tun (siehe "Stale devices are removed"
    in der HA-Integration-Quality-Scale-Dokumentation). Ohne das wuerde
    z.B. ein ueber den Options Flow abgewaehltes Modul (z.B. "n.a.")
    dauerhaft als Geraet sichtbar bleiben, auch nachdem es laut
    Konfiguration nicht mehr Teil der Integration ist.

    Wir KOENNEN hier sicher sein, dass ein fehlendes Modul tatsaechlich
    nicht mehr gewuenscht ist (im Gegensatz zum generischen HA-Beispiel,
    wo ein Geraet z.B. wegen eines voruebergehenden Verbindungsfehlers
    fehlen koennte) - die Modul-Auswahl ist eine explizite, vom Nutzer
    getroffene Entscheidung im Options Flow, kein voruebergehender
    Zustand.
    """

    device_registry = dr.async_get(hass)

    current_module_ids = {
        str(module.id)
        for module in system.modules
    }

    removed_count = 0

    for device_entry in dr.async_entries_for_config_entry(
        device_registry,
        entry.entry_id,
    ):

        for domain, identifier in device_entry.identifiers:

            if domain != DOMAIN:
                continue

            if not identifier.startswith("module2_"):
                continue

            module_id = identifier[
                len("module2_"):
            ]

            if module_id not in current_module_ids:

                device_registry.async_update_device(
                    device_id=device_entry.id,
                    remove_config_entry_id=entry.entry_id,
                )

                removed_count += 1

            break

    if removed_count:

        _LOGGER.info(
            "%d nicht mehr ausgewaehlte(s) Modul-Geraet(e) "
            "entfernt",
            removed_count,
        )


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


async def _reconcile_entities(
    hass: HomeAssistant,
    entry: ConfigEntry,
    system: WindhagerSystem,
) -> None:
    """Entities entfernen, die zu einem FRUEHEREN Zeitpunkt erstellt
    wurden (z.B. eine Sensor-Gruppe, die frueher ausgewaehlt war),
    aber bei der AKTUELLEN Gruppen-Auswahl (system.oid_map, bereits
    gefiltert durch selected_modules/selected_groups) nicht mehr
    vorkommen.

    Ergaenzt _reconcile_devices() um eine Ebene: ein Modul kann
    weiterhin ausgewaehlt sein (das Geraet existiert also weiter),
    aber EINZELNE Sensor-Gruppen darunter koennen ueber den Options
    Flow abgewaehlt worden sein - das faengt die Geraete-Bereinigung
    nicht ab, da das Geraet selbst ja bestehen bleibt.

    Beruecksichtigt auch DOMAIN-WECHSEL: wenn eine Entity frueher
    als 'sensor' angelegt wurde, jetzt aber (z.B. nach Einfuehrung
    von Write-Support) als 'select' oder 'number' erzeugt werden
    sollte, entfernt diese Funktion den alten 'sensor'-Eintrag,
    damit HA die Entity beim naechsten Setup in der richtigen Domain
    neu anlegen kann. Ohne das bleibt z.B. 'Betriebswahl' dauerhaft
    als unavailable sensor.* stehen, obwohl sie jetzt als select.*
    erzeugt werden wuerde.

    Selbes Muster wie bei _reconcile_devices() und
    _reconcile_entity_categories(): HA entfernt Entities, die eine
    Integration bei einem Setup-Durchlauf nicht mehr erzeugt, NICHT
    automatisch aus der Registry - das muss die Integration aktiv
    selbst tun. Ohne das wuerden abgewaehlte Sensor-Gruppen dauerhaft
    als "nicht verfuegbar" sichtbar bleiben, statt zu verschwinden.
    """

    registry = er.async_get(hass)

    removed_count = 0

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
            continue

        oid = unique_id[
            len("windhager_v2_"):
        ]

        if oid not in system.oid_map:

            registry.async_remove(
                entity_entry.entity_id
            )

            removed_count += 1
            continue

        # Domain-Wechsel pruefen: wenn die Entity als 'sensor'
        # registriert ist, aber jetzt als 'select' oder 'number'
        # erzeugt werden wuerde (z.B. durch nachtraeglich
        # eingefuehrten Write-Support), den alten Eintrag entfernen.
        if entity_entry.domain != "sensor":
            continue

        info = system.oid_map[oid]
        entry_obj = info["entry"]

        is_nv = oid.startswith("nv:")

        if is_nv:
            continue

        is_writable = not getattr(
            entry_obj,
            "write_protected",
            True,
        )

        if not is_writable:
            continue

        has_enum = bool(
            getattr(
                entry_obj,
                "enum",
                None,
            )
        )

        has_numeric_range = (
            entry_obj.min_value is not None
            and entry_obj.max_value is not None
            and not has_enum
        )

        if has_enum or has_numeric_range:

            registry.async_remove(
                entity_entry.entity_id
            )

            removed_count += 1

    if removed_count:

        _LOGGER.info(
            "%d veraltete(r) Sensor(en) entfernt "
            "(nicht mehr ausgewaehlt oder Domain-Wechsel)",
            removed_count,
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
        ["sensor", "number", "select"],
    )

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok