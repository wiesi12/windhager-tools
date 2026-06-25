import requests
from requests.auth import HTTPDigestAuth


class WindhagerClient:

    def __init__(self, host, username, password):

        self.host = host.rstrip("/")
        self.auth = HTTPDigestAuth(
            username,
            password
        )

    def get(self, path):

        url = f"http://{self.host}/api/1.0/{path}"

        response = requests.get(
            url,
            auth=self.auth,
            timeout=10
        )

        response.raise_for_status()

        return response.json()

    def lookup(self, path):

        return self.get(f"lookup/{path}")