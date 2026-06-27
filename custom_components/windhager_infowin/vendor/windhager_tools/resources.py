from xml.etree import ElementTree


class Resources:

    def __init__(self):

        self.lookup_names = {}
        self.entry_names = {}

    def load(self, client):

        self._load_lookup_names(client)
        self._load_entry_names(client)

    def _load_lookup_names(self, client):

        xml = client.resource(
            "xml/EbenenTexte_de.xml"
        )

        root = ElementTree.fromstring(xml)

        for function in root.findall("fcttyp"):

            for lookup in function.findall("ebene"):

                lookup_id = int(
                    lookup.attrib["id"]
                )

                self.lookup_names[
                    lookup_id
                ] = lookup.text or ""

    def _load_entry_names(self, client):

        xml = client.resource(
            "xml/VarIdentTexte_de.xml"
        )

        root = ElementTree.fromstring(xml)

        for group in root.findall("gn"):

            group_id = int(
                group.attrib["id"]
            )

            for member in group.findall("mn"):

                member_id = int(
                    member.attrib["id"]
                )

                self.entry_names[
                    (
                        group_id,
                        member_id,
                    )
                ] = member.text or ""

    def lookup_name(
        self,
        lookup_id,
    ):

        return self.lookup_names.get(
            lookup_id
        )

    def entry_name(
        self,
        group_id,
        member_id,
    ):

        return self.entry_names.get(
            (
                group_id,
                member_id,
            )
        )