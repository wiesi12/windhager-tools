import logging

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
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
        WindhagerSelect(
            coordinator,
            system,
            oid,
        )
        for oid in coordinator.data
        # Nur schreibbare, NICHT-NV-Entries MIT einem enum-Feld
        # (also Aufzaehlungs-Entries wie Betriebswahl, Heizprogramm).
        if not oid.startswith("nv:")
        and system.oid_map.get(oid) is not None
        and not getattr(
            system.oid_map[oid]["entry"],
            "write_protected",
            True,
        )
        and getattr(
            system.oid_map[oid]["entry"],
            "enum",
            None,
        )
    ]

    async_add_entities(entities)


class WindhagerSelect(
    CoordinatorEntity,
    SelectEntity,
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
    def options(self):
        """Liste der moeglichen Texte (nicht Rohwerte) fuer die HA-UI.

        Aus der AufzaehlTexte-Uebersetzung (system.enum_texts) wenn
        vorhanden, sonst als rohe Zahlenwerte aus entry.enum.
        """

        enum_values = self.entry.enum or []

        group = getattr(self.entry, "group", None)
        member = getattr(self.entry, "member", None)

        result = []

        for value in enum_values:

            if (
                group is not None
                and member is not None
                and self.system.enum_texts
            ):

                text = self.system.enum_texts.get(
                    (
                        group,
                        member,
                        value,
                    )
                )

                result.append(
                    text if text else str(value)
                )

            else:

                result.append(str(value))

        return result

    def _value_to_option(self, raw_value):
        """Rohen Enum-Wert in den Text fuer die HA-UI umwandeln."""

        try:

            int_value = int(raw_value)

        except (ValueError, TypeError):

            return str(raw_value)

        group = getattr(self.entry, "group", None)
        member = getattr(self.entry, "member", None)

        if (
            group is not None
            and member is not None
            and self.system.enum_texts
        ):

            text = self.system.enum_texts.get(
                (
                    group,
                    member,
                    int_value,
                )
            )

            if text:
                return text

        return str(int_value)

    def _option_to_value(self, option):
        """Text aus der HA-UI in den rohen Enum-Wert fuer die API umwandeln."""

        group = getattr(self.entry, "group", None)
        member = getattr(self.entry, "member", None)

        if (
            group is not None
            and member is not None
            and self.system.enum_texts
        ):

            for (g, m, v), text in self.system.enum_texts.items():

                if g == group and m == member and text == option:
                    return str(v)

        # Fallback: option ist schon ein Rohwert-String
        return option

    @property
    def current_option(self):

        live_value = (
            self.live_entry.value
            if self.live_entry is not None
            else self.entry.value
        )

        return self._value_to_option(live_value)

    async def async_select_option(
        self,
        option: str,
    ) -> None:

        raw_value = self._option_to_value(option)

        await self.hass.async_add_executor_job(
            self.system.client.write,
            self.entry.oid,
            raw_value,
        )

        _LOGGER.debug(
            "Wrote %s = %s (%s)",
            self.entry.oid,
            raw_value,
            option,
        )

        # Optimistischer Update: den gecachten Coordinator-Eintrag
        # sofort mit dem neuen Wert patchen und alle Listener
        # benachrichtigen - die UI zeigt sofort den neuen Wert, ohne
        # auf den naechsten regulaeren Poll zu warten (~5 Minuten).
        # Im Hintergrund dann einen echten Poll anstoossen
        # (async_refresh statt async_request_refresh, da letzteres
        # von HA debounced/ignoriert werden kann - verifiziert via
        # Live-Test).
        if (
            self.coordinator.data is not None
            and self.oid in self.coordinator.data
        ):
            self.coordinator.data[self.oid].value = raw_value

        self.coordinator.async_update_listeners()

        self.hass.async_create_task(
            self.coordinator.async_refresh()
        )
