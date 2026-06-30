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
        self.enum_texts = {}

    def load(self, client):

        self._load_lookup_names(client)
        self._load_entry_names(client)
        self._load_enum_texts(client)

    def _load_lookup_names(self, client):
        """EbenenTexte_<lang>.xml laden.

        WICHTIG: Die "ebene id" (Lookup-ID) ist NUR innerhalb eines
        "fcttyp" (Function-Typ) eindeutig, nicht global! Windhager
        vergibt z.B. "ebene id=100" sowohl unter fcttyp 14
        ("Ferienprogramm") als auch unter fcttyp 20
        ("Summenstörmeldung") - voellig unterschiedliche Bedeutung.
        Ein rein nach lookup_id indiziertes Dict wuerde bei solchen
        Kollisionen den falschen Namen liefern (je nachdem welcher
        fcttyp zuletzt in der XML-Datei vorkommt). Deshalb wird hier
        nach (fcttyp_id, lookup_id) geschluesselt; lookup_name()
        braucht entsprechend die function_type als Parameter.
        """

        xml = client.resource(
            f"xml/EbenenTexte_{self.language}.xml"
        )

        root = ElementTree.fromstring(xml)

        for function in root.findall("fcttyp"):

            function_type = int(
                function.attrib["id"]
            )

            for lookup in function.findall("ebene"):

                lookup_id = int(
                    lookup.attrib["id"]
                )

                self.lookup_names[
                    (
                        function_type,
                        lookup_id,
                    )
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

    def _load_enum_texts(self, client):
        """AufzaehlTexte_<lang>.xml laden - lesbare Texte fuer Enum-
        Werte (z.B. "0" -> "Standby" fuer "Betriebswahl").

        Adressierung folgt demselben (group, member)-Schema wie
        VarIdentTexte, mit einer zusaetzlichen Ebene fuer den
        konkreten Enum-Wert selbst:

            <gn id="3"><mn id="9"><enum id="0">Standby</enum></mn></gn>

        -> group_id=3, member_id=9, enum_value=0 -> "Standby"

        Nicht jede (group, member)-Kombination hat Enum-Texte (nur
        Eintraege, die laut typeId tatsaechlich Enums sind) - fehlende
        Kombinationen liefern entsprechend kein Ergebnis bei
        enum_text().
        """

        xml = client.resource(
            f"xml/AufzaehlTexte_{self.language}.xml"
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

                for enum in member.findall("enum"):

                    enum_value = int(
                        enum.attrib["id"]
                    )

                    self.enum_texts[
                        (
                            group_id,
                            member_id,
                            enum_value,
                        )
                    ] = enum.text or ""

    def lookup_name(
        self,
        function_type,
        lookup_id,
    ):

        return self.lookup_names.get(
            (
                function_type,
                lookup_id,
            )
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

    def enum_text(
        self,
        group_id,
        member_id,
        enum_value,
    ):

        return self.enum_texts.get(
            (
                group_id,
                member_id,
                enum_value,
            )
        )