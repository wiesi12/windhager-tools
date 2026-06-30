import time
from pathlib import Path

from homeassistant import config_entries
from homeassistant.helpers import selector
import voluptuous as vol

from .const import DATA_DIR, DOMAIN
from .language import resolve_language
from .lib import WindhagerClient
from .lib.catalog import load_catalog
from .lib.crawler import crawl_structure


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

    @staticmethod
    @config_entries.callback
    def async_get_options_flow(config_entry):

        return WindhagerOptionsFlow()

class WindhagerOptionsFlow(
    config_entries.OptionsFlowWithReload,
):
    """Erlaubt es, die Modul-/Sensor-Gruppen-Auswahl NACH der
    Ersteinrichtung zu aendern, ohne die Integration komplett neu
    einrichten zu muessen.

    Nutzt dasselbe Modul-fuer-Modul-Schritt-Muster wie der
    Erstinstallations-Flow (siehe WindhagerConfigFlow), aber mit zwei
    wichtigen Unterschieden:
    - Verwendet den bereits gespeicherten, VOLLSTAENDIGEN Katalog
      statt eine neue, langsame Discovery durchzufuehren (der Katalog
      wird ja bewusst ungefiltert gespeichert - siehe system.py).
    - Zeigt bei jeder Checkbox den AKTUELLEN, live gepollten Wert an
      (kostenlos verfuegbar, da der Coordinator zu diesem Zeitpunkt
      ja bereits laeuft - im Gegensatz zur Ersteinrichtung, wo eine
      Werte-Vorschau einen kompletten, zusaetzlichen Poll-Durchlauf
      noetig gemacht haette, siehe TODO.md fuer die Abwaegung).

    OptionsFlowWithReload (NICHT ein zusaetzlicher
    entry.add_update_listener() UND NICHT ein manueller
    await self.hass.config_entries.async_reload() innerhalb dieses
    Flows): laedt die Integration automatisch neu, sobald
    async_create_entry() zurueckkehrt. Beide Alternativen wurden
    versucht und verworfen:
    - Ein manueller async_reload()-Aufruf INNERHALB dieses Flow-
      Handlers fuehrte live getestet zu einem stillen Haenger (kein
      Fehler, der Flow schloss sich, aber nichts passierte) -
      vermutlich ein Deadlock um entry.setup_lock.
    - Ein zusaetzlicher update_listener (entry.add_update_listener())
      KOMBINIERT mit den eingebauten Reloading-Methoden des Flows ist
      seit HA 2026.6 explizit deprecated und wird ab 2026.12 zu einem
      Fehler ("kann zu doppeltem Reload oder einer Race Condition
      fuehren") - siehe https://developers.home-assistant.io/blog/2026/05/07/config-entry-listener-together-with-reloading-methods/
    Die offiziell empfohlene Loesung ist genau das hier: ausschliesslich
    auf die eingebauten Reloading-Methoden des Flows selbst verlassen
    (OptionsFlowWithReload), ohne zusaetzlichen Listener und ohne
    manuellen Reload-Aufruf.
    """

    def __init__(self):

        self._all_modules = None
        self._selected_modules = None
        self._module_index = 0
        self._selected_groups_by_module = {}

    async def async_step_init(
        self,
        user_input=None,
    ):

        # Den VOLLSTAENDIGEN, ungefilterten Katalog laden (nicht
        # system.modules, das ja bereits gefiltert ist) - genau dafuer
        # wurde der Katalog bewusst vollstaendig gespeichert.
        language = resolve_language(self.hass)

        catalog_path = (
            DATA_DIR
            / f"catalog_{language}.json"
        )

        def _load():

            all_modules, _ = load_catalog(
                catalog_path
            )

            return all_modules

        self._all_modules = (
            await self.hass.async_add_executor_job(
                _load
            )
        )

        return await self.async_step_select_modules()

    def _current_live_data(self):
        """Den laufenden Coordinator/System dieser Config-Entry
        finden, um Live-Werte fuer die Checkbox-Beschriftungen
        anzuzeigen. None, falls die Integration (noch) nicht laeuft
        (sollte im Options-Flow-Kontext eigentlich immer der Fall
        sein, aber sicherheitshalber abgefangen statt vorausgesetzt).
        """

        entry_data = self.hass.data.get(
            DOMAIN,
            {},
        ).get(
            self.config_entry.entry_id
        )

        if entry_data is None:
            return None, None

        return (
            entry_data["coordinator"].data,
            entry_data["nv_coordinator"].data,
        )

    def _format_module_label(self, module):

        coordinator_data, nv_data = (
            self._current_live_data()
        )

        if not coordinator_data and not nv_data:
            return module.name

        # Stichprobe: den ersten Entry mit einem nicht-leeren Live-
        # Wert in diesem Modul zeigen, als grobe Orientierung
        # ("was macht dieses Modul gerade"). Kein Anspruch auf
        # Vollstaendigkeit - nur ein zusaetzlicher Hinweis fuers Label.
        for function in module.functions:

            for lookup in function.lookups:

                for entry in lookup.entries:

                    oid = getattr(
                        entry,
                        "oid",
                        None,
                    )

                    if oid and coordinator_data:

                        live = coordinator_data.get(
                            oid
                        )

                        if (
                            live is not None
                            and live.value
                            not in (
                                None,
                                "-",
                            )
                        ):

                            return (
                                f"{module.name} "
                                f"(z.B. {lookup.name}: "
                                f"{live.value})"
                            )

        return module.name

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
                for module in self._all_modules
                if str(module.id) in selected_module_ids
            ]

            self._module_index = 0
            self._selected_groups_by_module = {}

            return await self.async_step_select_groups()

        previously_selected = set(
            self.config_entry.data.get(
                "selected_modules",
                [
                    str(module.id)
                    for module in self._all_modules
                ],
            )
        )

        options = [
            selector.SelectOptionDict(
                value=str(module.id),
                label=self._format_module_label(
                    module
                ),
            )
            for module in self._all_modules
        ]

        schema = vol.Schema(
            {
                vol.Required(
                    "modules",
                    default=sorted(
                        previously_selected
                    ),
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
        """Siehe WindhagerConfigFlow._current_module_lookup_keys()
        fuer die ausfuehrliche Begruendung des (function.type,
        lookup.id)-Schluessels (fcttyp-Kollisionen). Zusaetzlich hier:
        liefert auch das Live-Wert-Label pro Gruppe, falls verfuegbar.
        """

        module = self._selected_modules[
            self._module_index
        ]

        coordinator_data, nv_data = (
            self._current_live_data()
        )

        keys_with_labels = []

        for function in module.functions:

            for lookup in function.lookups:

                if not lookup.name:
                    continue

                key = f"{function.type}:{lookup.id}"

                label = lookup.name

                if (
                    lookup.entries
                    and coordinator_data
                ):

                    first_entry = lookup.entries[0]

                    oid = getattr(
                        first_entry,
                        "oid",
                        None,
                    )

                    if oid:

                        live = coordinator_data.get(
                            oid
                        )

                        if (
                            live is not None
                            and live.value
                            not in (
                                None,
                                "-",
                            )
                        ):

                            label = (
                                f"{lookup.name} "
                                f"({live.value})"
                            )

                keys_with_labels.append(
                    (
                        key,
                        label,
                    )
                )

        return module, keys_with_labels

    def _finish_module_and_advance(self):

        self._module_index += 1

        if self._module_index < len(
            self._selected_modules
        ):

            return None

        data = dict(self.config_entry.data)

        data["selected_modules"] = sorted(
            str(module.id)
            for module in self._selected_modules
        )

        data["selected_groups"] = (
            self._selected_groups_by_module
        )

        self.hass.config_entries.async_update_entry(
            self.config_entry,
            data=data,
        )

        # KEIN direkter async_reload()-Aufruf hier, und auch KEIN
        # entry.add_update_listener() in __init__.py: siehe Klassen-
        # Docstring fuer die Begruendung (beides wurde getestet und
        # verworfen - Deadlock bzw. seit HA 2026.6 deprecated wegen
        # moeglichen doppelten Reloads/Race Conditions). Stattdessen
        # uebernimmt OptionsFlowWithReload den Reload automatisch,
        # sobald async_create_entry() unten zurueckkehrt.
        #
        # WICHTIG: ein time.time()-Timestamp statt eines leeren {}
        # wird hier bewusst als "options" mitgegeben - live getestet
        # mit data={} loeste OptionsFlowWithReload den Reload NUR
        # INKONSISTENT aus (mal mit ein paar Sekunden Verzoegerung,
        # mal gar nicht), vermutlich weil die interne "haben sich die
        # Daten geaendert"-Pruefung von OptionsFlowWithReload auf den
        # HIER an async_create_entry() uebergebenen Wert schaut (der
        # in entry.options landet), nicht auf unsere SEPARATE
        # async_update_entry(data=...)-Aenderung oben. Ein garantiert
        # bei jedem Aufruf unterschiedlicher Wert macht den Reload
        # zuverlaessig, unabhaengig von dieser internen Logik. Der
        # konkrete Wert selbst hat keine funktionale Bedeutung - die
        # eigentliche Konfiguration steckt in entry.data (siehe oben).
        return self.async_create_entry(
            data={
                "_last_updated": time.time(),
            }
        )

    async def async_step_select_groups(
        self,
        user_input=None,
    ):

        module, keys_with_labels = (
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

        if not keys_with_labels:

            self._selected_groups_by_module[
                str(module.id)
            ] = []

            result = self._finish_module_and_advance()

            if result is not None:
                return result

            return await self.async_step_select_groups()

        previously_selected_groups = (
            self.config_entry.data.get(
                "selected_groups",
                {},
            ).get(
                str(module.id),
                [
                    key
                    for key, _ in keys_with_labels
                ],
            )
        )

        options = [
            selector.SelectOptionDict(
                value=key,
                label=label,
            )
            for key, label in keys_with_labels
        ]

        schema = vol.Schema(
            {
                vol.Required(
                    "groups",
                    default=previously_selected_groups,
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
