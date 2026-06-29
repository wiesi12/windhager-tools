from xml.etree import ElementTree


class TextDatabase:

    def __init__(self):

        self.levels = {}

    def load_levels(self, filename):

        tree = ElementTree.parse(filename)

        root = tree.getroot()

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

                self.levels[function_type][level_id] = (
                    level.text
                )

    def level_name(
        self,
        function_type,
        level_id,
    ):

        return self.levels.get(
            function_type,
            {},
        ).get(
            level_id,
        )