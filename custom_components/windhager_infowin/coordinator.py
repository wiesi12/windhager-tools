from datetime import timedelta
import logging

from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
)

from .const import DOMAIN


_LOGGER = logging.getLogger(__name__)


class WindhagerCoordinator(DataUpdateCoordinator):
    """Coordinator (Default: alle 5 Minuten) fuer die normalen OID-
    Sensoren. Bringt NV's zwar strukturell mit (Name, Index), aber
    OHNE deren teure Live-Wert-Abfrage - siehe WindhagerNvCoordinator
    fuer die tatsaechlichen NV-Werte.

    Hinweis: NV-Entities lesen ihren Wert nicht aus diesem
    Coordinator, sondern aus WindhagerNvCoordinator (siehe
    sensor.async_setup_entry) - ein Vermischen der Daten ist hier
    daher nicht noetig. self.system.poll() liefert NV's trotzdem mit
    (Platzhalterwert "-"), damit async_setup_entry beim allerersten
    Aufbau weiss, dass und mit welchem Schluessel diese Entities
    ueberhaupt existieren.
    """

    def __init__(self, hass, system, update_interval_minutes=5):

        super().__init__(
            hass,
            logger=_LOGGER,
            name=DOMAIN,
            update_interval=timedelta(
                minutes=update_interval_minutes
            ),
        )

        self.system = system

    async def _async_update_data(self):

        return await self.hass.async_add_executor_job(
            self.system.poll
        )


class WindhagerNvCoordinator(DataUpdateCoordinator):
    """Seltener Coordinator (Default: alle 10 Minuten) NUR fuer die
    tatsaechlichen NV-Live-Werte (Betriebsstunden, Pelletverbrauch
    etc.). Pro NV ist ein zusaetzlicher API-Call noetig (siehe
    reader.read_nv_value), daher bewusst getrennt vom haeufigen
    30s-Poll der normalen Sensoren.
    """

    def __init__(self, hass, system, update_interval_minutes=10):

        super().__init__(
            hass,
            logger=_LOGGER,
            name=f"{DOMAIN}_nv",
            update_interval=timedelta(
                minutes=update_interval_minutes
            ),
        )

        self.system = system

    async def _async_update_data(self):

        return await self.hass.async_add_executor_job(
            self.system.poll_nv
        )