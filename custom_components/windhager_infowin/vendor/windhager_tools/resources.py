from xml.etree import ElementTree


# Sprachen, fuer die Windhager fertige Uebersetzungsressourcen auf
# der Box bereitstellt (xml/EbenenTexte_<lang>.xml,
# xml/VarIdentTexte_<lang>.xml). "de" ist immer als Fallback
# verfuegbar; alle anderen Sprachen koennen je nach Firmware-Version
# fehlen, deshalb der Fallback-Mechanismus in load().
SUPPORTED_LANGUAGES = {
    "de",
    "en",
    "fr",
    "it",
}

DEFAULT_LANGUAGE = "de"


class Resources:

    def __init__(self, language=DEFAULT_LANGUAGE):

        # Unbekannte/nicht unterstuetzte Sprachen (z.B. "nl", weil
        # Windhager dafuer keine Ressourcendatei anbietet) fallen auf
        # Deutsch zurueck, statt beim Laden mit einem HTTP 404 zu
        # scheitern.
        self.language = (
            language
            if language in SUPPORTED_LANGUAGES
            else DEFAULT_LANGUAGE
        )

        self.lookup_names = {}
        self.entry_names = {}

    def load(self, client):

        self._load_lookup_names(client)
        self._load_entry_names(client)

    def _load_lookup_names(self, client):

        xml = client.resource(
            f"xml/EbenenTexte_{self.language}.xml"
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
            f"xml/VarIdentTexte_{self.language}.xml"
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