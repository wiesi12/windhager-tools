import logging

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from . import metadata
from . import naming
from .lib.slug import build_slug


_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities,
):

    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    system = hass.data[DOMAIN][entry.entry_id]["system"]

    entities = [
        WindhagerNumber(
            coordinator,
            system,
            oid,
        )
        for oid in coordinator.data
        # Nur schreibbare, NICHT-NV-Entries mit einem numerischen
        # Wert (also minValue/maxValue/step sind gesetzt, kein
        # Enum-Feld). NV-Entries haben kein write_protected-Attribut
        # und kein minValue/maxValue - die landen immer als Sensor.
        if not oid.startswith("nv:")
        and system.oid_map.get(oid) is not None
        and not getattr(
            system.oid_map[oid]["entry"],
            "write_protected",
            True,
        )
        and system.oid_map[oid]["entry"].min_value is not None
        and system.oid_map[oid]["entry"].max_value is not None
        and not getattr(
            system.oid_map[oid]["entry"],
            "enum",
            None,
        )
    ]

    async_add_entities(entities)


class WindhagerNumber(
    CoordinatorEntity,
    NumberEntity,
):

    _attr_has_entity_name = True
    _attr_mode = NumberMode.BOX

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

        return self.system.oid_map.get(self.oid)

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
    def live_entry(self):

        if self.coordinator.data is None:
            return None

        return self.coordinator.data.get(self.oid)

    @property
    def unique_id(self):

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
        )

    @property
    def name(self):

        if self.entry is None:
            return self.oid

        return naming.build_entity_name(
            self.entry,
            self.lookup,
        )

    @property
    def suggested_object_id(self):

        if self.info is None:
            return None

        return build_slug(
            self.info["module"],
            self.lookup,
            self.entry,
        )

    @property
    def native_value(self):

        live_value = (
            self.live_entry.value
            if self.live_entry is not None
            else self.entry.value
        )

        try:

            return float(
                str(live_value).replace(",", ".")
            )

        except (ValueError, TypeError):

            return None

    @property
    def native_min_value(self):

        try:

            return float(
                str(
                    self.entry.min_value
                ).replace(",", ".")
            )

        except (ValueError, TypeError):

            return 0.0

    @property
    def native_max_value(self):

        try:

            return float(
                str(
                    self.entry.max_value
                ).replace(",", ".")
            )

        except (ValueError, TypeError):

            return 100.0

    @property
    def native_step(self):

        if self.entry.step is None:
            return None

        try:

            return float(
                str(self.entry.step).replace(",", ".")
            )

        except (ValueError, TypeError):

            return None

    @property
    def native_unit_of_measurement(self):

        if self.entry is None:
            return None

        return metadata.translate_unit(
            self.entry.unit
        )

    @property
    def device_class(self):

        if self.entry is None:
            return None

        return metadata.device_class(self.entry)

    async def async_set_native_value(
        self,
        value: float,
    ) -> None:
        """Wert an die Box schreiben.

        step bestimmt die Anzahl der Dezimalstellen - wir formatieren
        entsprechend, statt float() direkt zu uebergeben (Windhager
        erwartet "12.5", nicht "12.500000000001").
        """

        step = self.entry.step

        if step is not None:

            try:

                step_float = float(
                    str(step).replace(",", ".")
                )

                decimal_places = max(
                    0,
                    len(
                        str(step_float).rstrip("0").split(".")[-1]
                    )
                    if "." in str(step_float)
                    else 0,
                )

                formatted = f"{value:.{decimal_places}f}"

            except (ValueError, TypeError):

                formatted = str(value)

        else:

            formatted = str(value)

        await self.hass.async_add_executor_job(
            self.system.client.write,
            self.entry.oid,
            formatted,
        )

        _LOGGER.debug(
            "Wrote %s = %s",
            self.entry.oid,
            formatted,
        )

        if (
            self.coordinator.data is not None
            and self.oid in self.coordinator.data
        ):
            self.coordinator.data[self.oid].value = formatted

        self.coordinator.async_update_listeners()

        self.hass.async_create_task(
            self.coordinator.async_refresh()
        )
