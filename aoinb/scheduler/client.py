
try:
    from httpx import Client
except ImportError:
    from requests import Session as Client

from ..common import stamps


class SchedulerClient:
    def __init__(self, client_name, client_key, server_url, server_key):
        self.client = Client()
        self.status = None
        self.client_name = client_name
        self.server_url = server_url
        self.signer = stamps.Signer(client_key)
        self.verifier = stamps.Verifier({server_url: server_key})
