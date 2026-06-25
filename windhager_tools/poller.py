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

        return values