import asyncio
import json
import contextlib
from typing import Dict, Set

from aiohttp import web

from sigmac3_sdk.clients import DBClient
from sigmac3_sdk.core.units import CabalUnit


class StreamHub:
    def __init__(self, db_client: DBClient, poll_interval: float = 1.0):
        self.db_client = db_client
        self.poll_interval = poll_interval
        self.clients: Dict[web.WebSocketResponse, Set[str]] = {}
        self.last_hash: Dict[str, str] = {}
        self.running = False
        self.task = None

    async def handle_ws(self, request: web.Request):
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        self.clients[ws] = set()
        try:
            async for msg in ws:
                if msg.type == web.WSMsgType.TEXT:
                    try:
                        payload = json.loads(msg.data)
                    except json.JSONDecodeError:
                        continue
                    if payload.get("action") == "subscribe":
                        types = payload.get("types") or []
                        self.clients[ws] = set(types)
                elif msg.type == web.WSMsgType.ERROR:
                    break
        finally:
            self.clients.pop(ws, None)
            await ws.close()
        return ws

    async def start(self, app: web.Application):
        self.running = True
        self.task = asyncio.create_task(self._loop())

    async def stop(self, app: web.Application):
        self.running = False
        if self.task:
            self.task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self.task

    async def _loop(self):
        while self.running:
            await self._broadcast_if_changed("units", key="unit_code")
            await self._broadcast_if_changed("tasks", key="task_id")
            await asyncio.sleep(self.poll_interval)

    async def _broadcast_if_changed(self, db_name: str, key: str):
        if self.db_client is None:
            return
        if not any(db_name in subs for subs in self.clients.values()):
            return
        try:
            rows = await asyncio.to_thread(self.db_client.get_all, db_name)
        except Exception:
            return
        if db_name == "units":
            formatted_units = []
            for raw in rows:
                unit = CabalUnit()
                unit.from_json(raw)
                formatted_units.append([
                    [unit.position.lat, unit.position.lon],
                    unit.sidc,
                    unit.callsign,
                    unit.get_name(),
                    unit.unit_code,
                ])
            rows_sorted = sorted(formatted_units, key=lambda r: r[4])
        else:
            rows_sorted = sorted(rows, key=lambda r: r.get(key, ""))
        blob = json.dumps(rows_sorted, sort_keys=True)
        if self.last_hash.get(db_name) == blob:
            return
        self.last_hash[db_name] = blob
        await self._broadcast({"type": db_name, "data": rows_sorted})

    async def _broadcast(self, message: dict):
        data = json.dumps(message)
        dead = []
        for ws, subs in self.clients.items():
            if message["type"] not in subs:
                continue
            try:
                await ws.send_str(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.clients.pop(ws, None)


def attach_stream_routes(app: web.Application, hub: StreamHub):
    app.router.add_get("/ws/stream", hub.handle_ws)
    app.on_startup.append(hub.start)
    app.on_cleanup.append(hub.stop)
    return hub
