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

        # Fuer die Lookup-Gruppen-Feinauswahl: pro ausgewaehltem Modul
        # eine EIGENE Formular-Seite, eine nach der anderen. HA hat
        # kein natives "wiederhole Schritt N mal"-Konzept im Config
        # Flow, daher verwalten wir den Fortschritt selbst: ein Index
        # in die Liste der ausgewaehlten Module, und ein Dict, das die
        # bereits getroffene Gruppen-Auswahl je Modul-ID sammelt,
        # bis alle Module durchlaufen sind.
        self._selected_modules = None
        self._module_index = 0
        self._selected_groups_by_module = {}

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

            self._selected_modules = [
                module
                for module in self._discovered_modules
                if str(module.id) in selected_module_ids
            ]

            self._module_index = 0
            self._selected_groups_by_module = {}

            return await self.async_step_select_groups()

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

    def _current_module_lookup_keys(self):
        """Fuer das aktuell bearbeitete Modul (self._module_index)
        alle eindeutigen Lookup-Gruppen-Schluessel sammeln.

        WICHTIG: lookup.id ist nur INNERHALB eines function.type
        eindeutig (siehe resources.py/crawler.py - Windhager vergibt
        z.B. "ebene id=100" sowohl fuer "Ferienprogramm" als auch fuer
        "Summenstoermeldung", je nach Function-Typ). Der eindeutige
        Schluessel ist daher "{function.type}:{lookup.id}", nicht nur
        lookup.id allein - sonst wuerden zwei inhaltlich komplett
        verschiedene Gruppen versehentlich als "dieselbe" Checkbox
        erscheinen bzw. gemeinsam de-/selektiert werden.

        Lookup-Gruppen ohne Namen (lookup.name == "") werden nicht als
        eigene Checkbox angezeigt - sie haben keinen sinnvoll
        anzeigbaren Titel und sollten bei "alle Gruppen" trotzdem
        automatisch enthalten sein, daher werden sie separat als
        "immer ausgewaehlt" behandelt (siehe async_step_select_groups).
        """

        module = self._selected_modules[
            self._module_index
        ]

        keys_with_names = []

        for function in module.functions:

            for lookup in function.lookups:

                if not lookup.name:
                    continue

                key = f"{function.type}:{lookup.id}"

                keys_with_names.append(
                    (
                        key,
                        lookup.name,
                    )
                )

        return module, keys_with_names

    def _finish_module_and_advance(self):
        """Nach Abschluss eines Moduls (egal ob per Formular-Submit
        oder weil es uebersprungen wurde) zum naechsten Modul gehen,
        oder - falls alle Module durch sind - die fertige Config-Entry
        erstellen. Gemeinsame Logik fuer beide Faelle in
        async_step_select_groups(), um Duplikation zu vermeiden.
        """

        self._module_index += 1

        if self._module_index < len(
            self._selected_modules
        ):

            return None

        data = dict(self._connection_data)

        data["selected_modules"] = sorted(
            str(module.id)
            for module in self._selected_modules
        )

        data["selected_groups"] = (
            self._selected_groups_by_module
        )

        return self.async_create_entry(
            title=self._connection_data["host"],
            data=data,
        )

    async def async_step_select_groups(
        self,
        user_input=None,
    ):

        module, keys_with_names = (
            self._current_module_lookup_keys()
        )

        if user_input is not None:

            self._selected_groups_by_module[
                str(module.id)
            ] = sorted(
                set(
                    user_input.get(
                        "groups",
                        [],
                    )
                )
            )

            result = self._finish_module_and_advance()

            if result is not None:
                return result

            return await self.async_step_select_groups()

        # Module ohne benannte Lookup-Gruppen (z.B. reine NV-Module
        # wie BioWIN, deren einzige Lookup-Gruppe "NV's" ohnehin
        # gesondert behandelt wird) ueberspringen die Checkbox-Seite
        # komplett - es gibt nichts sinnvoll Abwaehlbares.
        if not keys_with_names:

            self._selected_groups_by_module[
                str(module.id)
            ] = []

            result = self._finish_module_and_advance()

            if result is not None:
                return result

            return await self.async_step_select_groups()

        options = [
            selector.SelectOptionDict(
                value=key,
                label=name,
            )
            for key, name in keys_with_names
        ]

        all_keys = [
            key
            for key, _ in keys_with_names
        ]

        schema = vol.Schema(
            {
                vol.Required(
                    "groups",
                    default=all_keys,
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
            step_id="select_groups",
            data_schema=schema,
            description_placeholders={
                "module_name": module.name,
            },
        )