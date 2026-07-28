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
from .lib.nv_groups import groups_for_module, NV_GROUP_ORDER


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
        self._pending_data = {}
        self._pending_data = {}

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

                # "NV's" wird separat in async_step_select_nv_groups
                # behandelt - nicht als normale Checkbox anzeigen.
                if lookup.name == "NV's":
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

        # Zwischenspeichern - wird erst in async_step_poll_intervals
        # zusammen mit den Intervall-Einstellungen final committet.
        self._pending_data = data

        # Signalisiert dem Aufrufer (async_step_select_groups):
        # alle Module durch, weiter zum naechsten Schritt.
        return "ADVANCE_TO_POLL_INTERVALS"

    def _commit_and_reload(self, data):
        """Fertige Config in entry.data schreiben und Reload ausloesen.

        Ausgelagert damit async_step_poll_intervals() sauber committen
        kann. Siehe Klassen-Docstring fuer die Begruendung des
        time.time()-Timestamps (zuverlaessiger Reload via
        OptionsFlowWithReload).
        """

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
        # async_update_entry(data=...)-Aenderung oben.
        return self.async_create_entry(
            data={
                "_last_updated": time.time(),
            }
        )

    async def async_step_select_boiler(
        self,
        user_input=None,
    ):
        """Waermeerzeuger fuer die Geraete-Hierarchie auswaehlen
        (via_device).

        Eine automatische Erkennung ("das ist der Kessel") ist NICHT
        zuverlaessig moeglich - manche Waermeerzeuger (z.B. BioWIN)
        haben gar keinen aussagekraeftigen eigenen Funktionstyp,
        ihre Daten laufen komplett ueber NV-Variablen. Deshalb waehlt
        der Nutzer hier explizit, statt dass geraten wird. Default
        "none" = keine Hierarchie (heutiges Verhalten unveraendert).

        Nur bereits ausgewaehlte Module stehen zur Auswahl - ein
        via_device auf ein nicht angelegtes Geraet waere sonst ein
        haengender Verweis.
        """

        if user_input is not None:

            selected = user_input["boiler_module_id"]

            self._pending_data["boiler_module_id"] = (
                None
                if selected == "none"
                else int(selected)
            )

            return await self.async_step_poll_intervals()

        options = [
            selector.SelectOptionDict(
                value="none",
                label="None (flat device structure)",
            )
        ] + [
            selector.SelectOptionDict(
                value=str(module.id),
                label=module.name,
            )
            for module in self._selected_modules
        ]

        selected_ids = {
            str(module.id)
            for module in self._selected_modules
        }

        previous = self.config_entry.data.get(
            "boiler_module_id"
        )

        # Falls das zuvor gewaehlte Modul zwischenzeitlich abgewaehlt
        # wurde, auf "none" zurueckfallen statt einen ungueltigen
        # Default an den Selector zu uebergeben.
        default = (
            str(previous)
            if previous is not None
            and str(previous) in selected_ids
            else "none"
        )

        schema = vol.Schema(
            {
                vol.Required(
                    "boiler_module_id",
                    default=default,
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=options,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
            }
        )

        return self.async_show_form(
            step_id="select_boiler",
            data_schema=schema,
        )

    async def async_step_poll_intervals(
        self,
        user_input=None,
    ):
        """Poll-Intervalle konfigurieren.

        Letzter Schritt im Options Flow, direkt nach der Modul-/Gruppen-
        Auswahl. Speichert die gewaehlten Intervalle in entry.data und
        loest den Reload aus.

        Standardwerte: 1 Minute (Sensoren), 5 Minuten (NV-Werte).
        Sinnvoller Bereich: 1-60 Minuten fuer Sensoren, 1-60 Minuten
        fuer NVs. NVs schlagen sich pro NV-Index mit einem eigenen
        API-Call nieder - deshalb bewusst langsamer als Sensoren.
        """

        if user_input is not None:

            self._pending_data["poll_interval_minutes"] = (
                user_input["poll_interval_minutes"]
            )
            self._pending_data["nv_poll_interval_minutes"] = (
                user_input["nv_poll_interval_minutes"]
            )

            return await self.async_step_sensor_calibration()

        current_poll = self.config_entry.data.get(
            "poll_interval_minutes",
            1,
        )

        current_nv_poll = self.config_entry.data.get(
            "nv_poll_interval_minutes",
            5,
        )

        schema = vol.Schema(
            {
                vol.Required(
                    "poll_interval_minutes",
                    default=current_poll,
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=1,
                        max=60,
                        step=1,
                        unit_of_measurement="min",
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
                vol.Required(
                    "nv_poll_interval_minutes",
                    default=current_nv_poll,
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=1,
                        max=60,
                        step=1,
                        unit_of_measurement="min",
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
            }
        )

        return self.async_show_form(
            step_id="poll_intervals",
            data_schema=schema,
        )

    async def async_step_sensor_calibration(
        self,
        user_input=None,
    ):
        """Sensor-Kalibrierung konfigurieren.

        Aktuell: Pellet-Einheitenfaktor. Der Rohwert des NV-Sensors
        "Pellet Foerdermenge Summe" (NV-Index 19) hat eine
        anlagenabhaengige Einheit - auf der einzigen bisher getesteten
        Anlage (BioWIN 2 Touch) entspricht 1 Roheinheit 10 kg, d.h.
        der Faktor ist 10 (10.206 Roheinheiten = 102.06 t).

        Der Faktor wird als float in entry.data gespeichert und vom
        WindhagerPelletSensor in sensor.py angewendet. Default: 1.0
        (keine Umrechnung, Rohwert wird unveraendert angezeigt).
        """

        if user_input is not None:

            self._pending_data["pellet_unit_factor"] = (
                user_input["pellet_unit_factor"]
            )

            return self._commit_and_reload(
                self._pending_data
            )

        current_factor = self.config_entry.data.get(
            "pellet_unit_factor",
            1.0,
        )

        schema = vol.Schema(
            {
                vol.Required(
                    "pellet_unit_factor",
                    default=current_factor,
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=0.001,
                        max=1000.0,
                        step=0.001,
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
            }
        )

        return self.async_show_form(
            step_id="sensor_calibration",
            data_schema=schema,
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

            if result == "ADVANCE_TO_POLL_INTERVALS":
                return await self.async_step_select_nv_groups()

            if result is not None:
                return result

            return await self.async_step_select_groups()

        if not keys_with_labels:

            # None statt [] - damit _filter_modules_by_groups()
            # dieses Modul komplett unveraendert uebernimmt (alle
            # Lookups behalten). [] wuerde bedeuten "keine Lookups
            # ausgewaehlt" und alle Sensoren des Moduls loeschen.
            self._selected_groups_by_module[
                str(module.id)
            ] = None

            result = self._finish_module_and_advance()

            if result == "ADVANCE_TO_POLL_INTERVALS":
                return await self.async_step_select_nv_groups()

            if result is not None:
                return result

            return await self.async_step_select_groups()

        valid_keys = {key for key, _ in keys_with_labels}

        previously_selected_groups = [
            key
            for key in (
                self.config_entry.data.get(
                    "selected_groups",
                    {},
                ).get(
                    str(module.id),
                    [key for key, _ in keys_with_labels],
                )
            )
            # Nur Keys behalten die noch gueltig sind - verhindert
            # Validierungsfehler wenn sich die verfuegbaren Gruppen
            # geaendert haben (z.B. "NV's" nach Einfuehrung der
            # snvt-basierten NV-Gruppen-Auswahl).
            if key in valid_keys
        ]

        # Falls nach dem Filtern nichts uebrig bleibt (z.B. weil
        # ausschliesslich "NV's" gespeichert war): alle aktuellen
        # Gruppen als Default nehmen.
        if not previously_selected_groups:
            previously_selected_groups = [
                key for key, _ in keys_with_labels
            ]

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

    async def async_step_select_nv_groups(
        self,
        user_input=None,
    ):
        """NV-Gruppen (snvt-basiert) fuer alle Module mit NV-Eintraegen
        auswaehlen.

        Taucht nur auf wenn mindestens ein ausgewaehltes Modul
        NV-Eintraege hat. Die Gruppen basieren auf dem standardisierten
        LON-Typ snvt_name (nicht auf NV-Namen) und sind daher
        anlagenunabhaengig.

        Alle Gruppen sind standardmaessig ausgewaehlt (= gleiches
        Verhalten wie bisher, Rueckwaertskompatibilitaet).
        """

        # _selected_modules kommt aus crawl_structure (keine Entries),
        # _all_modules kommt aus load_catalog (volle NvEntry-Objekte).
        # Fuer die NV-Gruppen-Erkennung brauchen wir die Entries.
        # Beim Ersteinrichtungs-Flow (WindhagerConfigFlow) gibt es kein
        # _all_modules - in dem Fall Schritt ueberspringen und alle
        # NV-Gruppen verwenden (Default).
        all_modules = getattr(self, "_all_modules", None)

        if all_modules is None:
            return await self.async_step_select_boiler()

        selected_ids = {
            str(m.id) for m in self._selected_modules
        }
        catalog_modules = [
            m for m in all_modules
            if str(m.id) in selected_ids
        ]

        nv_groups = []
        for module in catalog_modules:
            for grp in groups_for_module(module):
                if grp not in nv_groups:
                    nv_groups.append(grp)

        # In definierter Reihenfolge sortieren
        nv_groups.sort(
            key=lambda g: NV_GROUP_ORDER.index(g[0])
            if g[0] in NV_GROUP_ORDER
            else 999
        )

        # Kein Modul hat NV-Eintraege -> ueberspringen
        if not nv_groups:
            return await self.async_step_select_boiler()

        if user_input is not None:
            self._pending_data["selected_nv_groups"] = (
                user_input.get("nv_groups", [])
            )
            return await self.async_step_select_boiler()

        previously_selected = self.config_entry.data.get(
            "selected_nv_groups",
            # Default: alle Gruppen ausgewaehlt
            [key for key, _ in nv_groups],
        )

        options = [
            selector.SelectOptionDict(
                value=key,
                label=label,
            )
            for key, label in nv_groups
        ]

        schema = vol.Schema(
            {
                vol.Required(
                    "nv_groups",
                    default=previously_selected,
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
            step_id="select_nv_groups",
            data_schema=schema,
        )
