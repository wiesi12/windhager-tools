import logging

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from . import naming
from .lib.slug import build_slug


_LOGGER = logging.getLogger(__name__)


def _is_boolean_entry(entry):
    """Prueft ob ein Entry ein Boolean-Wert ist (min=0, max=1, step=1).

    Die Windhager-API liefert fuer Boolean-Entries (z.B. "Freigabe
    starten") kein enum-Feld, aber einen numerischen Bereich von 0-1
    mit unit_id=0 (dimensionslos). 0 = Aus/Nein, 1 = Ein/Ja.

    Kriterien:
    - writeProt: false
    - min_value == "0" oder 0
    - max_value == "1" oder 1
    - kein enum-Feld
    - unit_id == 0

    Verifiziert auf: BioWIN 2 (MES INFINITY), "WW-Ladefreigabe
    Freigabe starten" (OID /1/17/0/2/16/0).
    Ob 0=Aus/1=Ein universell gilt, ist auf anderen Anlagen
    nicht verifiziert.
    """

    try:
        min_val = float(str(entry.min_value).replace(",", "."))
        max_val = float(str(entry.max_value).replace(",", "."))
    except (ValueError, TypeError):
        return False

    return (
        min_val == 0.0
        and max_val == 1.0
        and not getattr(entry, "enum", None)
        and getattr(entry, "unit_id", None) == 0
    )


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities,
):

    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    system = hass.data[DOMAIN][entry.entry_id]["system"]

    entities = [
        WindhagerSwitch(
            coordinator,
            system,
            oid,
        )
        for oid in coordinator.data
        if not oid.startswith("nv:")
        and system.oid_map.get(oid) is not None
        and not getattr(
            system.oid_map[oid]["entry"],
            "write_protected",
            True,
        )
        and system.oid_map[oid]["entry"].min_value is not None
        and system.oid_map[oid]["entry"].max_value is not None
        and _is_boolean_entry(system.oid_map[oid]["entry"])
    ]

    async_add_entities(entities)


class WindhagerSwitch(
    CoordinatorEntity,
    SwitchEntity,
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
    def _raw_value(self) -> str | None:

        live_value = (
            self.live_entry.value
            if self.live_entry is not None
            else self.entry.value
            if self.entry is not None
            else None
        )

        return str(live_value) if live_value is not None else None

    @property
    def is_on(self) -> bool | None:

        raw = self._raw_value

        if raw is None:
            return None

        try:
            return float(raw.replace(",", ".")) != 0.0
        except (ValueError, TypeError):
            return None

    async def async_turn_on(self, **kwargs) -> None:

        await self._write("1")

    async def async_turn_off(self, **kwargs) -> None:

        await self._write("0")

    async def _write(self, value: str) -> None:

        await self.hass.async_add_executor_job(
            self.system.client.write,
            self.entry.oid,
            value,
        )

        _LOGGER.debug(
            "Wrote %s = %s",
            self.entry.oid,
            value,
        )

        if (
            self.coordinator.data is not None
            and self.oid in self.coordinator.data
        ):
            self.coordinator.data[self.oid].value = value

        self.coordinator.async_update_listeners()

        self.hass.async_create_task(
            self.coordinator.async_refresh()
        )
