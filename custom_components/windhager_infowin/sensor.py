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
    system = hass.data[DOMAIN][entry.entry_id]["system"]

    entities = [
        WindhagerSensor(
            coordinator,
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

        return metadata.metadata(
            self.entry,
            self.lookup,
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

        return self.meta.get(
            "device_class"
        )

    @property
    def icon(self):

        return self.meta.get(
            "icon"
        )

    @property
    def native_value(self):

        return self.coordinator.data[
            self.oid
        ].value

    @property
    def native_unit_of_measurement(self):

        if not self.meta.get(
            "numeric",
            False,
        ):
            return None

        return self.entry.unit

    @property
    def suggested_display_precision(self):

        return self.meta.get(
            "precision"
        )