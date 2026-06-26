from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities,
):

    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    system = hass.data[DOMAIN][entry.entry_id]["system"]

    entities = []

    for oid in coordinator.data:

        entities.append(
            WindhagerSensor(
                coordinator,
                system,
                oid,
            )
        )

    async_add_entities(entities)


class WindhagerSensor(
    CoordinatorEntity,
    SensorEntity,
):

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
    def unique_id(self):

        return self.oid

    @property
    def name(self):

        info = self.system.oid_map.get(self.oid)

        if info is None:
            return self.oid

        module = info["module"]
        function = info["function"]

        return f"{module.name} - {function.name}"

    @property
    def native_value(self):

        return self.coordinator.data[self.oid].value

    @property
    def native_unit_of_measurement(self):

        return self.coordinator.data[self.oid].unit