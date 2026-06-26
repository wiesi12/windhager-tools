from xml.etree import ElementTree


class ResourceDatabase:

    def __init__(self):

        self.levels = {}
        self.variables = {}

    def load(self, client):

        self._load_levels(client)
        self._load_variables(client)

    def _load_levels(self, client):

        xml = client.resource(
            "xml/EbenenTexte_de.xml"
        )

        root = ElementTree.fromstring(xml)

        for function in root.findall("fcttyp"):

            function_type = int(
                function.attrib["id"]
            )

            self.levels.setdefault(
                function_type,
                {},
            )

            for level in function.findall("ebene"):

                level_id = int(
                    level.attrib["id"]
                )

                self.levels[
                    function_type
                ][
                    level_id
                ] = level.text

    def _load_variables(self, client):

        xml = client.resource(
            "xml/VarIdentTexte_de.xml"
        )

        root = ElementTree.fromstring(xml)

        for group in root.findall("gn"):

            group_id = int(
                group.attrib["id"]
            )

            self.variables.setdefault(
                group_id,
                {},
            )

            for member in group.findall("mn"):

                member_id = int(
                    member.attrib["id"]
                )

                self.variables[
                    group_id
                ][
                    member_id
                ] = member.text

    def level_name(
        self,
        function_type,
        level_id,
    ):

        return self.levels.get(
            function_type,
            {},
        ).get(level_id)

    def variable_name(
        self,
        group_id,
        member_id,
    ):

        return self.variables.get(
            group_id,
            {},
        ).get(member_id)