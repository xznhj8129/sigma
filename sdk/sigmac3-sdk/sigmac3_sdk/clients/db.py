import requests


class DBClient:
    def __init__(self, base_url="http://localhost:5001/api", auth_token=None):
        self.base_url = base_url.rstrip("/")
        self.auth_token = auth_token

    def _headers(self):
        headers = {}
        if self.auth_token:
            headers["x-auth-token"] = self.auth_token
        return headers

    def get_all(self, db_name):
        response = requests.get(f"{self.base_url}/{db_name}", headers=self._headers())
        response.raise_for_status()
        return response.json()

    def get(self, db_name, key, value):
        params = {"key": key, "value": value}
        response = requests.get(f"{self.base_url}/{db_name}", params=params, headers=self._headers())
        response.raise_for_status()
        return response.json()

    def insert(self, db_name, payload):
        data = {"data": payload}
        response = requests.post(f"{self.base_url}/{db_name}", json=data, headers=self._headers())
        response.raise_for_status()
        return response.json()

    def update(self, db_name, key, value, payload):
        data = {"data": payload}
        response = requests.put(f"{self.base_url}/{db_name}/{key}/{value}", json=data, headers=self._headers())
        response.raise_for_status()
        return response.json()

    def delete(self, db_name, key, value):
        response = requests.delete(f"{self.base_url}/{db_name}/{key}/{value}", headers=self._headers())
        response.raise_for_status()
        return response.json()
