from homeassistant import config_entries
from homeassistant.helpers import selector
import voluptuous as vol

from .const import DOMAIN
from .language import resolve_language
from .vendor.windhager_tools import WindhagerClient
from .vendor.windhager_tools.crawler import crawl_structure


class WindhagerConfigFlow(
    config_entries.ConfigFlow,
    domain=DOMAIN,
):

    VERSION = 1

    def __init__(self):

        # Wird zwischen den einzelnen Config-Flow-Schritten benoetigt:
        # async_step_user sammelt die Zugangsdaten, fuehrt die leicht-
        # gewichtige Struktur-Discovery durch (crawl_structure - OHNE
        # die teuren Werte-Calls), und async_step_select_modules
        # zeigt darauf basierend die Modul-Checkbox-Liste an. Eine
        # Flow-Instanz lebt nur fuer die Dauer dieses einen Setup-
        # Vorgangs, daher ist es hier sicher, den Discovery-Stand
        # zwischen den Schritten auf self zu halten.
        self._connection_data = None
        self._discovered_modules = None

    async def async_step_user(
        self,
        user_input=None,
    ):

        errors = {}

        if user_input is not None:

            client = WindhagerClient(
                user_input["host"],
                user_input["username"],
                user_input["password"],
            )

            language = resolve_language(self.hass)

            try:

                modules = await self.hass.async_add_executor_job(
                    crawl_structure,
                    client,
                    language,
                )

            except Exception:  # noqa: BLE001 - bewusst breit, da

                # die zugrunde liegende windhager_tools-Bibliothek
                # keine eigene, differenzierte Exception-Hierarchie
                # fuer Verbindungs-/Auth-/Parsing-Fehler bereitstellt
                # (siehe windhager_tools/client.py) - ein einzelner,
                # generischer Fehlertext im Formular ist hier die
                # praktikabelste Option, ohne library-weite Aenderungen
                # vorzunehmen.

                errors["base"] = "cannot_connect"

            else:

                self._connection_data = user_input
                self._discovered_modules = modules

                return await self.async_step_select_modules()

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
            errors=errors,
        )

    async def async_step_select_modules(
        self,
        user_input=None,
    ):

        if user_input is not None:

            selected_module_ids = set(
                user_input["modules"]
            )

            data = dict(self._connection_data)

            # Modul-IDs als Strings speichern (Config-Entry-Daten
            # muessen JSON-serialisierbar sein; die SelectSelector-
            # Werte sind ohnehin bereits Strings, siehe options unten).
            data["selected_modules"] = sorted(
                selected_module_ids
            )

            return self.async_create_entry(
                title=self._connection_data["host"],
                data=data,
            )

        options = [
            selector.SelectOptionDict(
                value=str(module.id),
                label=module.name,
            )
            for module in self._discovered_modules
        ]

        all_module_ids = [
            str(module.id)
            for module in self._discovered_modules
        ]

        schema = vol.Schema(
            {
                vol.Required(
                    "modules",
                    default=all_module_ids,
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=options,
                        multiple=True,
                        mode=selector.SelectSelectorMode.LIST,
                    )
                ),
            }
        )

        return self.async_show_form(
            step_id="select_modules",
            data_schema=schema,
        )