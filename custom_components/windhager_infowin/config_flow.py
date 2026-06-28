from homeassistant import config_entries
from homeassistant.helpers import selector
import voluptuous as vol

from .const import DOMAIN


class WindhagerConfigFlow(
    config_entries.ConfigFlow,
    domain=DOMAIN,
):

    VERSION = 1

    async def async_step_user(
        self,
        user_input=None,
    ):

        if user_input is not None:

            return self.async_create_entry(
                title=user_input["host"],
                data=user_input,
            )

        schema = vol.Schema(
            {
                vol.Required("host"): selector.TextSelector(),
                vol.Required("username"): selector.TextSelector(
                    selector.TextSelectorConfig(
                        autocomplete="username",
                    )
                ),
                # WICHTIG: TextSelectorType.PASSWORD sorgt dafuer,
                # dass HA das Feld im UI als maskierte Eingabe
                # (Punkte statt Klartext) anzeigt - ohne diesen
                # Selector wird das Passwort sonst im Klartext
                # eingegeben UND angezeigt (auch beim spaeteren
                # Bearbeiten der Integration in den Einstellungen).
                vol.Required("password"): selector.TextSelector(
                    selector.TextSelectorConfig(
                        type=selector.TextSelectorType.PASSWORD,
                        autocomplete="current-password",
                    )
                ),
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
        )