from windhager.reader import read_lookup


class Poller:

    def __init__(self, client, modules):

        self.client = client
        self.modules = modules

    def poll(self):

        results = []

        for module in self.modules:

            for function in module.functions:

                for lookup in function.lookups:

                    entries = read_lookup(
                        self.client,
                        module,
                        function,
                        lookup
                    )

                    results.extend(entries)

        return results