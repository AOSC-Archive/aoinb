
try:
    from httpx import Client
except ImportError:
    from requests import Session as Client


class SchedulerClient:
    def __init__(self, base_url):
        self.base_url = base_url
        self.client = Client()
        self.status = None


