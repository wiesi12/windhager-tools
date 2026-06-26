from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .vendor.windhager_tools import (
    WindhagerClient,
    WindhagerSystem,
)

from .const import DOMAIN
from .coordinator import WindhagerCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> bool:

    client = WindhagerClient(
        entry.data["host"],
        entry.data["username"],
        entry.data["password"],
    )

    system = WindhagerSystem(client)

    await hass.async_add_executor_job(
        system.initialize
    )

    coordinator = WindhagerCoordinator(
        hass,
        system,
    )

    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})

    hass.data[DOMAIN][entry.entry_id] = {
        "system": system,
        "coordinator": coordinator,
    }

    await hass.config_entries.async_forward_entry_setups(
        entry,
        ["sensor"],
    )

    return True


async def async_unload_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> bool:

    unload_ok = await hass.config_entries.async_unload_platforms(
        entry,
        ["sensor"],
    )

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok