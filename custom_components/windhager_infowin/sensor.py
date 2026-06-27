from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from . import metadata


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

        return self.oid

    @property
    def device_info(self):

        if self.info is None:
            return None

        module = self.info["module"]

        return DeviceInfo(
            identifiers={
                (
                    DOMAIN,
                    f"module_{module.id}",
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

        parts = []

        if self.lookup.name:
            parts.append(
                self.lookup.name
            )
        else:
            parts.append(
                f"Gruppe {self.entry.group}"
            )

        if self.entry.name:
            parts.append(
                self.entry.name
            )
        else:
            parts.append(
                f"Member {self.entry.member}"
            )

        return " | ".join(parts)

    @property
    def entity_category(self):

        return self.meta.get(
            "entity_category"
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