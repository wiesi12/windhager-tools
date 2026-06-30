"""Tests fuer lib/resources.py.

Schwerpunkt: die fcttyp-Kollisions-Logik bei lookup_name() - der
subtilste Bug, der in diesem Projekt gefunden wurde (siehe README/
TODO/Git-History fuer den vollen Kontext). Windhager vergibt
"ebene id"-Werte nur INNERHALB eines fcttyp eindeutig, nicht global -
ein und dieselbe Lookup-ID kann je nach Function-Typ etwas voellig
anderes bedeuten (z.B. "100" = "Ferienprogramm" bei fcttyp 14, aber
"Summenstoermeldung" bei fcttyp 20).
"""

from lib.resources import Resources


class FakeClient:
    """Minimaler Client-Stand-in, der fest hinterlegte XML-Inhalte
    statt echter HTTP-Requests liefert.
    """

    def __init__(self, responses):
        self.responses = responses

    def resource(self, path):
        return self.responses[path]


def _client_with_ebenen_texte(xml_content):

    return FakeClient(
        {
            "xml/EbenenTexte_de.xml": xml_content,
            "xml/VarIdentTexte_de.xml": (
                "<VarIdentTexte></VarIdentTexte>"
            ),
            "xml/AufzaehlTexte_de.xml": (
                "<AufzaehlTexte></AufzaehlTexte>"
            ),
        }
    )


def test_lookup_name_resolves_simple_case():

    client = _client_with_ebenen_texte(
        """<EbenenTexte lang="de">
            <fcttyp id="14">
                <ebene id="96">Betriebswahl</ebene>
            </fcttyp>
        </EbenenTexte>"""
    )

    resources = Resources("de")
    resources.load(client)

    assert (
        resources.lookup_name(14, 96)
        == "Betriebswahl"
    )


def test_lookup_name_distinguishes_same_id_across_function_types():
    """Der eigentliche Regressionstest fuer den fcttyp-Kollisions-
    Bug: zwei VERSCHIEDENE fcttyp-Gruppen verwenden dieselbe
    "ebene id" (hier: 100) fuer voellig unterschiedliche Dinge -
    das darf sich NICHT gegenseitig ueberschreiben.

    Dies sind die tatsaechlichen, am 2026-06-28 live von einer echten
    Windhager-Box beobachteten Werte (siehe Git-History fuer den
    vollen Kontext).
    """

    client = _client_with_ebenen_texte(
        """<EbenenTexte lang="de">
            <fcttyp id="14">
                <ebene id="100">Ferienprogramm</ebene>
            </fcttyp>
            <fcttyp id="20">
                <ebene id="100">Summenst&#246;rmeldung</ebene>
            </fcttyp>
        </EbenenTexte>"""
    )

    resources = Resources("de")
    resources.load(client)

    assert (
        resources.lookup_name(14, 100)
        == "Ferienprogramm"
    )
    assert (
        resources.lookup_name(20, 100)
        == "Summenstörmeldung"
    )


def test_lookup_name_returns_none_for_unknown_combination():

    client = _client_with_ebenen_texte(
        """<EbenenTexte lang="de">
            <fcttyp id="14">
                <ebene id="96">Betriebswahl</ebene>
            </fcttyp>
        </EbenenTexte>"""
    )

    resources = Resources("de")
    resources.load(client)

    assert resources.lookup_name(99, 99) is None


def test_entry_name_resolves_group_member():

    client = FakeClient(
        {
            "xml/EbenenTexte_de.xml": (
                "<EbenenTexte></EbenenTexte>"
            ),
            "xml/VarIdentTexte_de.xml": (
                """<VarIdentTexte>
                    <gn id="3">
                        <mn id="50">bis Datum</mn>
                    </gn>
                </VarIdentTexte>"""
            ),
            "xml/AufzaehlTexte_de.xml": (
                "<AufzaehlTexte></AufzaehlTexte>"
            ),
        }
    )

    resources = Resources("de")
    resources.load(client)

    assert (
        resources.entry_name(3, 50)
        == "bis Datum"
    )


def test_enum_text_resolves_group_member_value():
    """Regressionstest fuer das Enum-Uebersetzungs-Feature (z.B.
    "0" -> "Standby" fuer "Betriebswahl"). Adressierung folgt einer
    zusaetzlichen Ebene gegenueber entry_name(): (group, member,
    enum_value) statt nur (group, member).
    """

    client = FakeClient(
        {
            "xml/EbenenTexte_de.xml": (
                "<EbenenTexte></EbenenTexte>"
            ),
            "xml/VarIdentTexte_de.xml": (
                "<VarIdentTexte></VarIdentTexte>"
            ),
            "xml/AufzaehlTexte_de.xml": (
                """<AufzaehlTexte>
                    <gn id="3">
                        <mn id="50">
                            <enum id="0">Standby</enum>
                            <enum id="1">Heizprogramm 1</enum>
                        </mn>
                    </gn>
                </AufzaehlTexte>"""
            ),
        }
    )

    resources = Resources("de")
    resources.load(client)

    assert (
        resources.enum_text(3, 50, 0)
        == "Standby"
    )
    assert (
        resources.enum_text(3, 50, 1)
        == "Heizprogramm 1"
    )


def test_enum_text_returns_none_for_unknown_value():

    client = FakeClient(
        {
            "xml/EbenenTexte_de.xml": (
                "<EbenenTexte></EbenenTexte>"
            ),
            "xml/VarIdentTexte_de.xml": (
                "<VarIdentTexte></VarIdentTexte>"
            ),
            "xml/AufzaehlTexte_de.xml": (
                """<AufzaehlTexte>
                    <gn id="3">
                        <mn id="50">
                            <enum id="0">Standby</enum>
                        </mn>
                    </gn>
                </AufzaehlTexte>"""
            ),
        }
    )

    resources = Resources("de")
    resources.load(client)

    # Bekannte (group, member), aber unbekannter enum_value
    assert resources.enum_text(3, 50, 99) is None

    # Komplett unbekannte (group, member)
    assert resources.enum_text(1, 1, 0) is None


def test_unsupported_language_falls_back_to_default():
    """Nicht unterstuetzte Sprachen (z.B. "nl", fuer die Windhager
    keine Ressourcendatei anbietet) sollen auf Deutsch zurueckfallen,
    statt beim Laden mit einem HTTP 404 zu scheitern.
    """

    resources = Resources("nl")

    assert resources.language == "de"
