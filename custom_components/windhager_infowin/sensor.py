from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN


DIAGNOSTIC_LOOKUPS = {
    "Modulinfo",
}


DEVICE_CLASSES = {
    "°C": SensorDeviceClass.TEMPERATURE,
    "K": SensorDeviceClass.TEMPERATURE,
    "bar": SensorDeviceClass.PRESSURE,
    "V": SensorDeviceClass.VOLTAGE,
    "A": SensorDeviceClass.CURRENT,
    "Hz": SensorDeviceClass.FREQUENCY,
    "W": SensorDeviceClass.POWER,
    "kW": SensorDeviceClass.POWER,
    "Wh": SensorDeviceClass.ENERGY,
    "kWh": SensorDeviceClass.ENERGY,
}


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

        lookup = self.info["lookup"]
        entry = self.info["entry"]

        parts = []

        if lookup.name:
            parts.append(
                lookup.name
            )
        else:
            parts.append(
                f"Gruppe {entry.group}"
            )

        if entry.name:
            parts.append(
                entry.name
            )
        else:
            parts.append(
                f"Member {entry.member}"
            )

        return " | ".join(parts)

    @property
    def entity_category(self):

        if self.info is None:
            return None

        lookup = self.info["lookup"]

        if lookup.name in DIAGNOSTIC_LOOKUPS:
            return EntityCategory.DIAGNOSTIC

        return None

    @property
    def device_class(self):

        unit = self.native_unit_of_measurement

        if unit is None:
            return None

        return DEVICE_CLASSES.get(unit)

    @property
    def native_value(self):

        return self.coordinator.data[
            self.oid
        ].value

    @property
    def native_unit_of_measurement(self):

        value = self.native_value

        try:

            float(
                str(value).replace(
                    ",",
                    ".",
                )
            )

            return self.coordinator.data[
                self.oid
            ].unit

        except Exception:

            return None

    @property
    def suggested_display_precision(self):

        unit = self.native_unit_of_measurement

        if unit == "°C":
            return 1

        if unit == "%":
            return 0

        return None