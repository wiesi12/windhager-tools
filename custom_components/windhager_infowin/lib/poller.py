from .reader import read_lookup


class Poller:

    def __init__(self, client, modules):

        self.client = client
        self.modules = modules

    def poll(self):
        """Haeufiger Poll (z.B. alle 30s): alle normalen OID-Sensoren
        plus NV-Struktur (aber ohne die teuren NV-Detail-Calls -
        NV-Werte bleiben hier auf ihrem zuletzt bekannten Stand, bis
        poll_nv() sie aktualisiert).
        """

        return self._poll(fetch_nv_values=False)

    def poll_nv(self):
        """Seltener, teurer Poll (z.B. alle 10 Minuten): aktualisiert
        NUR die NV-Werte (ein zusaetzlicher API-Call PRO NV). Liefert
        ein Dict im gleichen nv:{module_id}:{index}-Schema, das in
        die bestehenden coordinator.data-Werte eingemischt wird.
        """

        return self._poll(
            fetch_nv_values=True,
            oid_entries=False,
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