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

    def resource(self, path):

        url = f"http://{self.host}/res/{path}"

        response = requests.get(
            url,
            auth=self.auth,
            timeout=self.timeout,
        )

        response.raise_for_status()

        return response.text