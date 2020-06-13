import falcon
import builder
from enum import Enum


class BuildBackend(object):
    class Status(Enum):
        IDLE: 0
        BUILDING: 1
        LOADING_OS: 2
        UPDATING_OS: 3

    work_dir: str
    config_path: str
    status: Status

    def __init__(self, work_dir: str, config_path: str):
        self.work_dir = work_dir
        self.config_path = config_path
        self.status = self.Status.IDLE

    def update_status(self):
        pass

    def build(self):
        pass

    def load_os(self):
        pass

    def update_os(self):
        pass


class StatusAPI(object):
    def on_get(self, req, resp):
        response = "I'm doing good!"
        resp.body = response

        resp.status = falcon.HTTP_200


class BuildAPI(object):
    def __init__(self, build_backend):
        building: bool = False

    def on_get(self, req, resp):
        pass


app = falcon.API()

build_backend = BuildBackend("todo", "todo")
build_api = BuildAPI(build_backend)

status_api = StatusAPI()

app.add_route('/get_status', status_api)
app.add_route('/build', build_api)
