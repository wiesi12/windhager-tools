from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from . import metadata
from . import naming
from .vendor.windhager_tools.slug import build_slug


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities,
):

    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    nv_coordinator = hass.data[DOMAIN][entry.entry_id]["nv_coordinator"]
    system = hass.data[DOMAIN][entry.entry_id]["system"]

    entities = [
        WindhagerSensor(
            # NV-Entities (Schluessel "nv:...") werden beim
            # nv_coordinator registriert, damit sie bei dessen
            # selteneren Updates (Standard: alle 10 Minuten) neu
            # geschrieben werden. Alle anderen (normale OID-Sensoren)
            # bleiben am haeufigen 30s-coordinator.
            nv_coordinator if oid.startswith("nv:") else coordinator,
            system,
            oid,
        )
        for oid in coordinator.data
    ]

    async_add_entities(entities)


class WindhagerSensor(
    CoordinatorEntity,
    SensorEntity,
):

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator,
        system,
        oid,
    ):

        super().__init__(coordinator)

        self.system = system
        self.oid = oid

    @property
    def info(self):

        return self.system.oid_map.get(
            self.oid
        )

    @property
    def entry(self):

        if self.info is None:
            return None

        return self.info["entry"]

    @property
    def lookup(self):

        if self.info is None:
            return None

        return self.info["lookup"]

    @property
    def meta(self):

        if self.entry is None:
            return {}

        # WICHTIG: self.entry kommt aus dem statischen Katalog
        # (system.oid_map) und enthaelt bei NV's immer den
        # Platzhalterwert "-" aus der Discovery-Phase, NICHT den
        # aktuellen Live-Wert. metadata.metadata() entscheidet aber
        # u.a. anhand des Werts, ob der Sensor numerisch ist (siehe
        # has_numeric_value). Deshalb hier den aktuellen Live-Wert aus
        # dem Coordinator einsetzen, bevor die Metadaten berechnet
        # werden - sonst bleiben device_class/unit/precision dauerhaft
        # auf Basis des veralteten Katalog-Platzhalters falsch gesetzt.
        live_value = self.coordinator.data[
            self.oid
        ].value

        return metadata.metadata(
            self.entry,
            self.lookup,
            live_value,
        )

    @property
    def unique_id(self):

        # WICHTIG: Dieses Präfix darf in Zukunft nicht mehr geändert
        # werden, sobald die Integration produktiv läuft! Ändert sich
        # unique_id, legt HA einen komplett NEUEN Registry-Eintrag an
        # (alter Eintrag wird verwaist) - das ist hier bewusst so
        # gewollt, um sicherzustellen, dass suggested_object_id beim
        # allerersten Anlegen ausgewertet wird und nicht ein alter,
        # bereits unter dieser unique_id bestehender Eintrag (mit
        # seiner historisch festgelegten entity_id) wiederverwendet
        # wird.
        return f"windhager_v2_{self.oid}"

    @property
    def device_info(self):

        if self.info is None:
            return None

        module = self.info["module"]

        return DeviceInfo(
            identifiers={
                (
                    DOMAIN,
                    f"module2_{module.id}",
                )
            },
            manufacturer="Windhager",
            model="InfoWIN",
            name=module.name,
        )

    @property
    def name(self):

        if self.info is None:
            return self.oid

        return naming.build_entity_name(
            self.entry,
            self.lookup,
        )

    @property
    def suggested_object_id(self):
        """Stabilen, lesbaren Object-ID-Vorschlag liefern.

        Wird unabhängig vom (ggf. zusammengesetzten/übersetzten)
        Anzeigenamen aus Modul/Lookup/Entry abgeleitet, damit die
        entity_id auch bei Änderungen an naming.build_entity_name()
        stabil bleibt und keine Kollisionen/Suffixe (_2, _3, ...)
        durch Zufall entstehen.

        module.name wird hier bewusst NICHT mit verarbeitet (siehe
        build_slug in slug.py): Home Assistant stellt bei
        has_entity_name=True automatisch Area- und Geräte-Namen vor
        diesen Object-Id-Teil, sonst entstünde eine Dopplung.
        """

        if self.info is None:
            return None

        module = self.info["module"]

        return build_slug(
            module,
            self.lookup,
            self.entry,
        )

    @property
    def entity_category(self):

        return self.meta.get(
            "entity_category"
        )

    @property
    def entity_registry_enabled_default(self):

        return self.meta.get(
            "enabled_by_default",
            True,
        )

    @property
    def device_class(self):

        # "valid" statt "numeric": Datum/Zeit-Werte sind nicht
        # numerisch (has_numeric_value), aber trotzdem ein gueltiger,
        # typisierter Wert (has_valid_value) - device_class soll fuer
        # beide Faelle gesetzt werden, sofern der Wert kein
        # Platzhalter ("-") ist.
        if not self.meta.get(
            "valid",
            False,
        ):
            return None

        return self.meta.get(
            "device_class"
        )

    @property
    def state_class(self):

        # metadata.state_class() liefert bereits None fuer nicht-
        # numerische Werte und fuer device_classes, bei denen HA
        # keinen state_class erlaubt (DATE, ENUM, ...) - hier nur
        # noch durchreichen.
        return self.meta.get(
            "state_class"
        )

    @property
    def icon(self):

        return self.meta.get(
            "icon"
        )

    @property
    def native_value(self):

        # metadata.parsed_value() wandelt Datum/Zeit-Strings ("20"/
        # "21" Einheit) in echte date/time-Objekte um, wie von HA fuer
        # device_class DATE/TIME gefordert. Fuer alle anderen Faelle
        # liefert es den unveraenderten Rohwert.
        live_value = self.coordinator.data[
            self.oid
        ].value

        return metadata.parsed_value(
            self.entry,
            live_value,
        )

    @property
    def native_unit_of_measurement(self):

        if not self.meta.get(
            "numeric",
            False,
        ):
            return None

        # Bevorzugt die Einheit aus dem aktuellen Live-Wert (falls
        # vorhanden), da self.entry.unit der statische Katalog-Wert
        # ist. In der Praxis aendert sich die Einheit einer Variable
        # nicht zur Laufzeit, aber so bleibt es konsistent mit der
        # live_value-Logik in self.meta.
        live_entry = self.coordinator.data.get(
            self.oid
        )

        raw_unit = (
            live_entry.unit
            if live_entry is not None and live_entry.unit
            else self.entry.unit
        )

        # Windhager liefert teils eigene/deutsche Einheitenkuerzel
        # (z.B. "Std" statt "h"), die HA fuer die jeweilige
        # device_class nicht akzeptiert - hier auf die von HA
        # erwartete Einheit uebersetzen.
        return metadata.translate_unit(raw_unit)

    @property
    def suggested_display_precision(self):

        # Wie bei native_unit_of_measurement: precision darf nur
        # gesetzt werden, wenn der Wert tatsaechlich numerisch ist.
        # Sonst denkt HA, der Sensor sei numerisch, obwohl er (noch)
        # einen Platzhalterwert wie "-" liefert, und stuerzt beim
        # Schreiben des States ab.
        if not self.meta.get(
            "numeric",
            False,
        ):
            return None

        return self.meta.get(
            "precision"
        )