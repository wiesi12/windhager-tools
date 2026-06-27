from windhager_tools.reader import read_lookup


class Poller:

    def __init__(self, client, modules):

        self.client = client
        self.modules = modules

    def poll(self):

        values = {}

        for module in self.modules:

            for function in module.functions:

                for lookup in function.lookups:

                    entries = read_lookup(
                        self.client,
                        module,
                        function,
                        lookup
                    )

                    for entry in entries:

                        if hasattr(entry, "oid"):

                            values[entry.oid] = entry

                        elif hasattr(entry, "index"):

                            # Gleiches Schluessel-Schema wie in
                            # WindhagerSystem.build_oid_map(), damit
                            # NvEntry-Werte beim Polling demselben
                            # Eintrag in oid_map zugeordnet werden.
                            nv_key = f"nv:{module.id}:{entry.index}"

                            values[nv_key] = entry

        return values