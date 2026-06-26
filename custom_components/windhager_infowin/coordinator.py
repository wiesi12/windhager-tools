from datetime import timedelta
import logging

from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
)

from .const import DOMAIN


_LOGGER = logging.getLogger(__name__)


class WindhagerCoordinator(DataUpdateCoordinator):

    def __init__(self, hass, system):

        super().__init__(
            hass,
            logger=_LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=30),
        )

        self.system = system

    async def _async_update_data(self):

        return await self.hass.async_add_executor_job(
            self.system.poll
        )