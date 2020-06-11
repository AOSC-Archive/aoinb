#!/usr/bin/env python3
import asyncio
import websockets
from websockets import WebSocketServerProtocol
import re
from api_server.builder_api import BuilderAPIServer


class APIServer:
    builder_api: BuilderAPIServer
    def __init__(self):
        builder_api = BuilderAPIServer()

    async def ws_handler(self, ws: WebSocketServerProtocol, path: str):
        async for msg in ws:
            if re.match("^/builder", path):
                await self.builder_api.builder_handler(ws, msg)


api_server = APIServer()
start_server = websockets.serve(api_server.ws_handler, "localhost", 4000)

asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()
