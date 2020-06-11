from websockets import WebSocketServerProtocol
import json
import logging
from typing import List, Union

from type_definitions import Job

logging.basicConfig(level=logging.INFO)

class Builder:
    ws: WebSocketServerProtocol
    name: str
    arch: str
    speed: int

    def __init__(self, ws, name, arch, speed):
        self.ws = ws
        self.name = name
        self.arch = arch
        self.speed = speed

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
            print("Bad request!")
            print(json.dumps(j, sort_keys=True, indent=4))
            return False

        current_builders: List[str] = []
        for b in self.builders:
            current_builders.append(b.name)

        if builder_name not in map(Builder.get_name, self.builders):
            self.builders.append(Builder(ws, builder_name, builder_arch, builder_speed))
            response = {
                "type": "hello",
                "result": "success"
            }
            await ws.send(json.dumps(response))
            return True
        else:
            response = {
                "type": "hello",
                "result": "failed",
                "reason": "Another buildbot with name " + builder_name + "already existed."
            }
            await ws.send(json.dumps(response))
            return False

    async def bye(self, b: Builder):
        res = {"type": "bye", "result": "success"}
        await b.ws.send(json.dumps(res))
        await b.ws.close()
        self.builders.remove(b)

    async def new_job(self, j: Job):
        pass

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
