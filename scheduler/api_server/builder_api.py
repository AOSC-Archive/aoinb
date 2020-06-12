from websockets import WebSocketServerProtocol
import json
import logging
from enum import Enum
from typing import List, Union

from type_definitions import Job

logging.basicConfig(level=logging.INFO)


class Builder:
    class State(Enum):
        IDLE = 0
        FETCHING = 1
        BUILDING = 2

    ws: WebSocketServerProtocol
    name: str
    arch: str
    speed: int
    state: State

    def __init__(self, ws, name, arch, speed):
        self.ws = ws
        self.name = name
        self.arch = arch
        self.speed = speed
        self.state = Builder.State.IDLE

    def get_name(self) -> str:
        return self.name


class BuilderAPIServer:
    builders: List[Builder] = []

    async def hello(self, ws: WebSocketServerProtocol, j: json) -> bool:
        try:
            builder_name = j['builder']['name']
            builder_arch = j['builder']['architecture']
            builder_speed = j['builder']['speed']
        except json.JSONDecodeError:
            print('Bad request! You have not registered yet.')
            print(json.dumps(j, sort_keys=True, indent=4))
            return False

        current_builders: List[str] = []
        for b in self.builders:
            current_builders.append(b.name)

        if builder_name not in map(Builder.get_name, self.builders):
            self.builders.append(Builder(ws, builder_name, builder_arch, builder_speed))
            response = {
                'type': 'hello',
                'result': 'success'
            }
            await ws.send(json.dumps(response))
            return True
        else:
            response = {
                'type': 'hello',
                'result': 'failed',
                'reason': 'Another buildbot with name ' + builder_name + 'already existed.'
            }
            await ws.send(json.dumps(response))
            return False

    async def bye(self, b: Builder):
        res = {'type': 'bye', 'result': 'success'}
        await b.ws.send(json.dumps(res))
        await b.ws.close()
        self.builders.remove(b)

    async def new_job(self, j: Job):
        request = {
            'type': 'new_job',
            'result': None,  # In theory this will be converted to null by json module
            'job': j.get_json_map()
        }
        # TODO: Implement scheduling
        idling_builders = filter(lambda b: b.state == Builder.State.IDLE,
                                 self.builders)
        try:
            # For now we just use the first idling builder
            builder: Builder = next(idling_builders)
            await builder.ws.send(json.dumps(request))
        except StopIteration:
            logging.warning('No builder available!')

    async def new_job_response(self, b: Builder, j: json):
        if b.state == Builder.State.IDLE and ['status'] == 'success':
            b.state = Builder.State.FETCHING

    async def new_builder_handler(self, ws: WebSocketServerProtocol, msg: str):
        try:
            j: json = json.loads(msg)
        except json.JSONDecodeError:
            await ws.send('Bad request!')
            return

        req_type = j['type']
        if req_type == 'hello':
            await self.hello(ws, j)
        else:
            await ws.send('Bad request!')
            await ws.close()
            return

    async def existing_builder_handler(self, b: Builder, msg: Union[str, bytes]):
        # Bytes cannot be handled by normal JSON routine. Detect this first.
        # TODO: Implement binary data save.
        if type(msg) is bytes:
            print('Ya sent me some bytes!')
            return

        try:
            j: json = json.loads(msg)
        except json.JSONDecodeError:
            await b.ws.send('Bad request!')
            return

        req_type = j['type']
        if req_type == 'bye':
            await self.bye(b)
        elif req_type == 'new_job':
            await self.new_job_response(b, j)

    async def builder_handler(self, ws: WebSocketServerProtocol, msg):
        registered_builders = []
        for b in self.builders:
            registered_builders.append(b.ws)

        if ws in registered_builders:
            # Use a separate function to deal with our old friend's request
            b: Builder = next(filter(lambda x: x.ws == ws, self.builders))
            await self.existing_builder_handler(b, msg)
        else:
            # Otherwise, help them register if asked nicely
            await self.new_builder_handler(ws, msg)
