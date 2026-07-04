from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMAIN


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities,
):

    entry_data = hass.data[DOMAIN][entry.entry_id]

    async_add_entities(
        [
            WindhagerRefreshButton(
                entry,
                entry_data["coordinator"],
                "coordinator",
                "Jetzt aktualisieren",
                "mdi:refresh",
                "windhager_refresh_now",
            ),
            WindhagerRefreshButton(
                entry,
                entry_data["nv_coordinator"],
                "nv_coordinator",
                "NV-Werte aktualisieren",
                "mdi:database-refresh",
                "windhager_nv_refresh_now",
            ),
        ]
    )


class WindhagerRefreshButton(ButtonEntity):
    """Loest einen sofortigen Coordinator-Refresh aus.

    Nuetzlich wenn man nach einer Aenderung (z.B. Betriebswahl
    umgestellt) nicht auf das naechste regulaere Poll-Intervall
    warten moechte.

    Verwendet async_request_refresh() statt async_refresh():
    - async_refresh() ist blockierend und laeuft sofort durch
    - async_request_refresh() ist debounced (standardmaessig 1s),
      aber das ist hier voellig in Ordnung - ein Button-Druck ist
      kein zeitkritischer Vorgang, und die Debounce verhindert
      versehentliche Doppel-Refreshes bei schnellem Klicken.
    """

    _attr_has_entity_name = True
    _attr_entity_category = None  # sichtbar, kein diagnostic

    def __init__(
        self,
        entry,
        coordinator,
        coordinator_key,
        name,
        icon,
        unique_id_suffix,
    ):

        self._entry = entry
        self._coordinator = coordinator
        self._attr_name = name
        self._attr_icon = icon
        self._attr_unique_id = f"windhager_v2_{unique_id_suffix}"

    @property
    def device_info(self):

        # Dem ersten Modul-Geraet zuordnen (Modul 2, ID 60 ist
        # typischerweise der BioWIN-Kessel). Faellt zurueck auf
        # ein generisches "Windhager" Geraet wenn kein spezifisches
        # Modul gefunden wird.
        return DeviceInfo(
            identifiers={
                (
                    DOMAIN,
                    "module2_60",
                )
            },
        )

    async def async_press(self) -> None:

        await self._coordinator.async_request_refresh()
