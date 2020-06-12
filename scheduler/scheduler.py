#!/usr/bin/env python3
import asyncio
import websockets
from websockets import WebSocketServerProtocol
import re
from type_definitions import Job, Package
from api_server.builder_api import BuilderAPIServer

import uuid

class APIServer:
    builder_api: BuilderAPIServer

    def __init__(self):
        self.builder_api = BuilderAPIServer()

    async def ws_handler(self, ws: WebSocketServerProtocol, path: str):
        async for msg in ws:
            print(path)
            if re.match("^/builder", path):
                await self.builder_api.builder_handler(ws, msg)
            elif re.match("^/test_build", path):
                pkgs = [Package("pkg1"), Package("pkg2"), Package("pkg3")]
                j = Job("bname", "bdescription", pkgs, ["amd46"])
                await self.builder_api.new_job(j)


api_server = APIServer()
start_server = websockets.serve(api_server.ws_handler, "localhost", 4000)

asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()
