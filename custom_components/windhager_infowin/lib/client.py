import requests
from requests.auth import HTTPDigestAuth


class WindhagerClient:

    def __init__(
        self,
        host,
        username,
        password,
        timeout=10,
    ):

        self.host = host.rstrip("/")
        self.timeout = timeout

        self.auth = HTTPDigestAuth(
            username,
            password,
        )

    def get(self, path):

        url = f"http://{self.host}/api/1.0/{path}"

        response = requests.get(
            url,
            auth=self.auth,
            timeout=self.timeout,
        )

        response.raise_for_status()

        return response.json()

    def lookup(self, path):

        return self.get(f"lookup/{path}")

    def write(self, oid, value):
        """Einen Wert an die Box schreiben.

        oid: OID-String wie "/1/15/0/3/50/0" (mit fuehrendem Slash,
             genau so wie er von der API geliefert wird - kein
             weiteres Formatieren noetig).
        value: neuer Wert als String (die API erwartet immer einen
               String, auch fuer numerische Werte).

        Verifiziert am 2026-06-29 via Browser-Entwicklertools: das
        offizielle Windhager-Webinterface nutzt exakt diesen Endpunkt
        und dieses Format, und funktioniert mit dem ENDUSER-Account
        (USER/Passwort), den diese Integration ohnehin schon fuer
        lesende Abfragen verwendet.
        """

        url = f"http://{self.host}/api/1.0/datapoint"

        response = requests.put(
            url,
            json={
                "OID": oid,
                "value": str(value),
            },
            auth=self.auth,
            timeout=self.timeout,
        )

        response.raise_for_status()

    def get_object(self, oid):
        """Komplexes Objekt (z.B. Zeitprogramm) lesen.

        oid: voller OID-String inkl. fuehrendem Slash und Instanz-
        Segment, z.B. "/1/15/0/3/61/0".

        Anders als lookup()/get(): dieser Endpunkt erwartet EINEN
        einzelnen Query-Parameter "OID" mit dem vollen Pfad - NICHT
        node_id/function_id/oid getrennt (das liefert 500 "Wrong
        formatted OID:''"). Verifiziert am 2026-07-28 via Browser-
        Entwicklertools/direktem Test gegen die eigene Anlage: liefert
        fuer Zeitprogramme (typeId 30) den vollen Wert inkl.
        switchPoints/weekdays, was der normale lookup()-Endpunkt fuer
        diese Objekte nie tut.
        """

        url = f"http://{self.host}/api/1.0/object"

        response = requests.get(
            url,
            params={"OID": oid},
            auth=self.auth,
            timeout=self.timeout,
        )

        response.raise_for_status()

        return response.json()

    def write_object(
        self,
        node_id,
        function_id,
        oid_path,
        oid,
        subtype_id,
        type_id,
        value,
    ):
        """Komplexes Objekt (z.B. Zeitprogramm) schreiben.

        node_id/function_id/oid_path bilden die Query-Parameter
        dieses Endpunkts (node_id=..&function_id=..&oid=<lookup>/
        <member>) - anders als bei get_object() erwartet der PUT hier
        die Adressierung getrennt, nicht als ein einzelner OID-
        Parameter. oid/subtype_id/type_id/value bilden den Body.

        Exakt das Format, das auch die offizielle Windhager-Cloud-API
        (connect-api.windhager.com) nutzt - lokal verifiziert am
        2026-07-28 mit dem bereits aktiven Wert eines Zeitprogramms
        (No-Op-Test, Status 200).
        """

        url = f"http://{self.host}/api/1.0/object"

        response = requests.put(
            url,
            params={
                "node_id": node_id,
                "function_id": function_id,
                "oid": oid_path,
            },
            json={
                "OID": oid,
                "subtypeId": subtype_id,
                "typeId": type_id,
                "value": value,
            },
            auth=self.auth,
            timeout=self.timeout,
        )

        response.raise_for_status()

    def resource(self, path):

        url = f"http://{self.host}/res/{path}"

        response = requests.get(
            url,
            auth=self.auth,
            timeout=self.timeout,
        )

        response.raise_for_status()

        return response.text