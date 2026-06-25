from datetime import timedelta

from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
)

from .const import DOMAIN


class WindhagerCoordinator(DataUpdateCoordinator):

    def __init__(self, hass, system):

        super().__init__(
            hass,
            logger=None,
            name=DOMAIN,
            update_interval=timedelta(seconds=30),
        )

        self.system = system

    async def _async_update_data(self):

        return await self.hass.async_add_executor_job(
            self.system.poll
        )