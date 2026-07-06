from .reader import read_lookup


class Poller:

    def __init__(self, client, modules):

        self.client = client
        self.modules = modules

        # Change detection: letzten bekannten Stand fuer jeden Key
        # cachen. Nur Keys deren Wert sich seit dem letzten Poll
        # geaendert hat werden zurueckgegeben - unveraenderte Werte
        # werden aus dem Cache wiederverwendet.
        # Beim allerersten Poll ist der Cache leer, d.h. alle Werte
        # werden normal zurueckgegeben.
        self._last_values = {}

    def _apply_change_detection(self, new_values):
        """Nur tatsaechlich geaenderte Werte zurueckgeben.

        Vergleicht jeden Wert mit dem zuletzt gecachten Stand.
        Bei Uebereinstimmung wird der gecachte Entry wiederverwendet
        (spart Coordinator-Updates und HA-State-Writes).
        Neue Keys (noch nicht im Cache) werden immer durchgereicht.
        Cache wird nach jedem Aufruf aktualisiert.
        """

        result = {}

        for key, entry in new_values.items():

            last = self._last_values.get(key)

            # Wert hat sich geaendert (oder ist neu): durchreichen
            # und Cache aktualisieren.
            new_val = (
                entry.value
                if hasattr(entry, "value")
                else entry
            )
            last_val = (
                last.value
                if last is not None and hasattr(last, "value")
                else last
            )

            if last is None or new_val != last_val:
                result[key] = entry
                self._last_values[key] = entry
            else:
                # Unveraendert: gecachten Entry weiterverwenden
                # damit der Coordinator keine unnoetige State-
                # Aktualisierung ausloest.
                result[key] = last

        return result

    def poll(self):
        """Haeufiger Poll (z.B. alle 1 Minute): alle normalen OID-Sensoren
        plus NV-Struktur (aber ohne die teuren NV-Detail-Calls).
        Wendet Change Detection an - unveraenderte Werte loesen keinen
        neuen HA-State-Write aus.
        """

        return self._apply_change_detection(
            self._poll(fetch_nv_values=False)
        )

    def poll_nv(self):
        """Seltener, teurer Poll (z.B. alle 5 Minuten): aktualisiert
        NUR die NV-Werte. Wendet Change Detection an.
        """

        return self._apply_change_detection(
            self._poll(
                fetch_nv_values=True,
                oid_entries=False,
            )
        )

    def _poll(self, fetch_nv_values, oid_entries=True):

        values = {}

        for module in self.modules:

            for function in module.functions:

                for lookup in function.lookups:

                    is_nv_lookup = (
                        lookup.name == "NV's"
                    )

                    # Im NV-only-Poll (poll_nv) ueberspringen wir
                    # alle Nicht-NV-Lookups komplett, um unnoetige
                    # API-Calls zu vermeiden.
                    if not oid_entries and not is_nv_lookup:
                        continue

                    entries = read_lookup(
                        self.client,
                        module,
                        function,
                        lookup,
                        fetch_nv_values=(
                            fetch_nv_values
                            and is_nv_lookup
                        ),
                    )

                    for entry in entries:

                        if hasattr(entry, "oid"):

                            if oid_entries:
                                values[entry.oid] = entry

                        elif hasattr(entry, "index"):

                            # Gleiches Schluessel-Schema wie in
                            # WindhagerSystem.build_oid_map(), damit
                            # NvEntry-Werte beim Polling demselben
                            # Eintrag in oid_map zugeordnet werden.
                            nv_key = f"nv:{module.id}:{entry.index}"

                            values[nv_key] = entry

        return values