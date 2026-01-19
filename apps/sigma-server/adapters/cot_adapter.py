"""
Usage:
    python apps/sigma-server/adapters/cot_adapter.py --config apps/sigma-server/adapters/cot_adapter.yml
"""
import argparse
import datetime
import select
import socket
import struct
import time
import uuid
from dataclasses import dataclass
from typing import Iterable

import yaml
import pytz
import xmltodict

import frogcot
from sigmac3_sdk.clients.db import DBClient


RECV_BUFFER = 65535
MULTICAST_TTL = 2


@dataclass(frozen=True)
class Endpoint:
    host: str
    port: int


@dataclass(frozen=True)
class AdapterConfig:
    listen: Endpoint
    multicast: Endpoint | None
    tcp_listen: Endpoint | None
    tak_tcp_connect: Endpoint | None
    targets: list[Endpoint]
    takserver: Endpoint | None
    sigma_base_url: str
    sigma_auth_token: str | None
    sigma_push_db: str
    sigma_pull_dbs: list[str]
    poll_interval: float
    stale_seconds: int
    default_ce: float
    default_le: float
    self_callsign: str
    self_cottype: str
    min_write_interval: float
    loopback_ttl: float
    tak_db: str
    self_position: dict | None
    self_uid: str | None
    self_beacon_interval: float | None


class DatagramReceiver:
    def __init__(self, bind: Endpoint, multicast_group: str | None = None):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((bind.host, bind.port))
        if multicast_group:
            membership = struct.pack("=4sl", socket.inet_aton(multicast_group), socket.INADDR_ANY)
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, membership)
        sock.setblocking(False)
        self.socket = sock

    def recv(self) -> tuple[bytes, tuple[str, int]]:
        return self.socket.recvfrom(RECV_BUFFER)


class DatagramSender:
    def __init__(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, MULTICAST_TTL)
        self.socket = sock

    def send(self, payload: bytes, targets: Iterable[Endpoint]) -> None:
        for endpoint in targets:
            self.socket.sendto(payload, (endpoint.host, endpoint.port))


class TakServerSender:
    def __init__(self, endpoint: Endpoint):
        self.endpoint = endpoint
        self.socket: socket.socket | None = None

    def send(self, payload: bytes) -> None:
        if not self.socket:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(5)
            self.socket.connect((self.endpoint.host, self.endpoint.port))
            self.socket.settimeout(None)
        try:
            self.socket.sendall(payload)
        except OSError:
            self.close()
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(5)
            self.socket.connect((self.endpoint.host, self.endpoint.port))
            self.socket.settimeout(None)
            self.socket.sendall(payload)

    def close(self) -> None:
        if self.socket:
            try:
                self.socket.close()
            finally:
                self.socket = None


class TcpListener:
    def __init__(self, bind: Endpoint):
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind((bind.host, bind.port))
        srv.listen(5)
        srv.setblocking(False)
        self.server = srv
        self.buffers: dict[socket.socket, bytearray] = {}

    def sockets(self) -> list[socket.socket]:
        return [self.server] + list(self.buffers.keys())

    def owns(self, sock: socket.socket) -> bool:
        return sock in self.buffers

    def accept_ready(self) -> None:
        conn, _ = self.server.accept()
        conn.setblocking(False)
        self.buffers[conn] = bytearray()

    def recv_ready(self, sock: socket.socket) -> list[tuple[bytes, tuple[str, int]]]:
        data = sock.recv(RECV_BUFFER)
        if not data:
            self.close_conn(sock)
            return []
        buf = self.buffers[sock]
        buf.extend(data)
        events: list[tuple[bytes, tuple[str, int]]] = []
        marker = b"</event>"
        while True:
            idx = buf.find(marker)
            if idx == -1:
                break
            end = idx + len(marker)
            chunk = bytes(buf[:end])
            del buf[:end]
            try:
                addr = sock.getpeername()
            except OSError:
                addr = ("tcp", 0)
            events.append((chunk, addr))
        return events

    def close_conn(self, sock: socket.socket) -> None:
        try:
            sock.close()
        finally:
            self.buffers.pop(sock, None)


class TcpClientReceiver:
    def __init__(self, endpoint: Endpoint, reconnect_secs: float = 3.0):
        self.endpoint = endpoint
        self.reconnect_secs = reconnect_secs
        self.sock: socket.socket | None = None
        self.buffer = bytearray()
        self.next_attempt = time.monotonic()

    def socket(self) -> socket.socket | None:
        return self.sock

    def ensure_connected(self) -> None:
        now = time.monotonic()
        if self.sock or now < self.next_attempt:
            return
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(5)
            s.connect((self.endpoint.host, self.endpoint.port))
            s.setblocking(False)
            self.sock = s
            self.next_attempt = now + self.reconnect_secs
            print(f"tak_tcp_connected {self.endpoint.host}:{self.endpoint.port}")
        except OSError as exc:
            self.sock = None
            self.next_attempt = now + self.reconnect_secs
            print(f"tak_tcp_connect_failed {self.endpoint.host}:{self.endpoint.port} reason={exc}")

    def recv_ready(self) -> list[tuple[bytes, tuple[str, int]]]:
        if not self.sock:
            return []
        try:
            data = self.sock.recv(RECV_BUFFER)
        except OSError as exc:
            print(f"tak_tcp_recv_failed {self.endpoint.host}:{self.endpoint.port} reason={exc}")
            self._close()
            return []
        if not data:
            self._close()
            return []
        self.buffer.extend(data)
        marker = b"</event>"
        events = []
        while True:
            idx = self.buffer.find(marker)
            if idx == -1:
                break
            end = idx + len(marker)
            chunk = bytes(self.buffer[:end])
            del self.buffer[:end]
            events.append((chunk, (self.endpoint.host, self.endpoint.port)))
        return events

    def _close(self) -> None:
        if self.sock:
            try:
                self.sock.close()
            finally:
                self.sock = None
                self.buffer.clear()
                self.next_attempt = time.monotonic() + self.reconnect_secs


class CotTranslator:
    def __init__(self, stale_seconds: int, default_ce: float, default_le: float, self_callsign: str, self_cottype: str):
        self.stale_seconds = stale_seconds
        self.default_ce = default_ce
        self.default_le = default_le
        self.client = frogcot.ATAKClient(self_callsign, cottype=self_cottype, is_self=True)

    def parse_event(self, xml_text: str) -> frogcot.Event:
        try:
            return frogcot.xml_to_cot(xml_text)
        except ValueError:
            return self._parse_loose(xml_text)

    def _parse_loose(self, xml_text: str) -> frogcot.Event:
        data = xmltodict.parse(xml_text)["event"]
        point_data = data["point"]
        point = frogcot.Point(
            latitude=float(point_data["@lat"]),
            longitude=float(point_data["@lon"]),
            height_above_ellipsoid=float(point_data.get("@hae", 0.0)),
            circular_error=float(point_data.get("@ce", 0.0)),
            linear_error=float(point_data.get("@le", 0.0)),
        )
        version_raw = data.get("@version", 2)
        try:
            version = int(version_raw)
        except ValueError:
            version = int(float(version_raw))

        def parse_time(raw: str | None) -> datetime.datetime:
            if raw is None:
                return datetime.datetime.now(pytz.utc)
            return datetime.datetime.fromisoformat(raw.replace("Z", "+00:00"))

        detail = data.get("detail")
        if detail:
            detail = dict(detail)

        return frogcot.Event(
            point=point,
            detail=detail if detail else None,
            version=version,
            event_type=data.get("@type", ""),
            access=data.get("@access"),
            quality_of_service=data.get("@qos"),
            unique_id=data.get("@uid", str(uuid.uuid4())),
            time=parse_time(data.get("@time")),
            start=parse_time(data.get("@start")),
            stale=parse_time(data.get("@stale")),
            how=data.get("@how", ""),
        )

    def event_to_sigma(self, event: frogcot.Event, source: tuple[str, int]) -> dict:
        sidc = None
        try:
            sidc = frogcot.convert_cot_to_2525b(event.event_type)
        except ValueError:
            pass

        contact = None
        if event.detail and "contact" in event.detail:
            contact_node = event.detail["contact"]
            contact = contact_node.get("@callsign") or contact_node.get("callsign")

        payload = {
            "template_type": "intel_track",
            "type": "cot_track",
            "uid": event.unique_id,
            "unit_code": event.unique_id,
            "callsign": contact,
            "name": contact or event.unique_id,
            "num": 0,
            "category": "UNK",
            "size": "UNK",
            "taskforce": False,
            "cot": event.event_type,
            "sidc": sidc,
            "how": event.how,
            "time": event.time.isoformat(),
            "start": event.start.isoformat(),
            "stale": event.stale.isoformat(),
            "position": {
                "lat": event.point.latitude,
                "lon": event.point.longitude,
                "alt": event.point.height_above_ellipsoid,
                "ce": event.point.circular_error,
                "le": event.point.linear_error,
            },
            "detail": event.detail or {},
            "source": f"{source[0]}:{source[1]}",
            "sender_callsign": contact,
        }
        return payload

    def sigma_to_event_xml(self, record: dict) -> bytes:
        pos = self._position(record)
        cottype = record.get("cot")
        if not cottype:
            sidc = record.get("sidc")
            if not sidc:
                raise ValueError(f"Record {record.get('uid') or record.get('unit_code')} lacks cot and sidc")
            cottype = frogcot.convert_2525b_to_cot(sidc)
        callsign = (
            record.get("callsign")
            or record.get("name")
            or record.get("unit_code")
            or record.get("uid")
        )
        if not callsign:
            raise ValueError(f"Record {record.get('uid') or record.get('unit_code')} lacks callsign")
        uid = record.get("uid") or record.get("unit_code")
        if not uid:
            raise ValueError("Record missing uid and unit_code")
        staletime = record.get("stale_seconds") or self.stale_seconds
        return self.client.cot_marker(callsign, uid, cottype, pos, staletime=staletime)

    def _position(self, record: dict) -> dict:
        pos = record.get("position")
        if not pos:
            raise ValueError(f"Record {record.get('uid')} missing position")
        ce = pos.get("ce", self.default_ce)
        le = pos.get("le", self.default_le)
        return {
            "lat": pos["lat"],
            "lon": pos["lon"],
            "alt": pos.get("alt", 0.0),
            "ce": ce,
            "le": le,
        }


class SigmaTakAdapter:
    def __init__(self, config: AdapterConfig):
        self.config = config
        self.db = DBClient(base_url=config.sigma_base_url, auth_token=config.sigma_auth_token)
        self.translator = CotTranslator(
            stale_seconds=config.stale_seconds,
            default_ce=config.default_ce,
            default_le=config.default_le,
            self_callsign=config.self_callsign,
            self_cottype=config.self_cottype,
        )
        receivers: list[DatagramReceiver] = [DatagramReceiver(config.listen)]
        if config.multicast:
            receivers.append(DatagramReceiver(config.multicast, multicast_group=config.multicast.host))
        self.receivers = receivers
        self.sender = DatagramSender()
        self.takserver_sender = TakServerSender(config.takserver) if config.takserver else None
        self.socket_map = {rcv.socket.fileno(): rcv for rcv in receivers}
        try:
            self.tcp_listener = TcpListener(config.tcp_listen) if config.tcp_listen else None
        except OSError as exc:
            self.tcp_listener = None
            print(f"tcp_listen_disabled reason={exc}")
        self.tcp_client = TcpClientReceiver(config.tak_tcp_connect) if config.tak_tcp_connect else None
        self.last_writes: dict[str, tuple[tuple, float]] = {}
        self.sent_recent: dict[str, float] = {}
        self.self_uid = config.self_uid or config.self_callsign
        self.next_self_beacon = time.monotonic()
        print(f"adapter_listen={config.listen.host}:{config.listen.port} multicast={config.multicast.host + ':' + str(config.multicast.port) if config.multicast else 'none'} tcp_listen={f'{config.tcp_listen.host}:{config.tcp_listen.port}' if config.tcp_listen else 'none'} tcp_connect={f'{config.tak_tcp_connect.host}:{config.tak_tcp_connect.port}' if config.tak_tcp_connect else 'none'} targets={[f'{t.host}:{t.port}' for t in config.targets]} takserver={f'{config.takserver.host}:{config.takserver.port}' if config.takserver else 'none'} push_db={config.sigma_push_db} pull_dbs={config.sigma_pull_dbs} tak_db={config.tak_db}")

    def run(self) -> None:
        next_poll = time.monotonic()
        sockets = [rcv.socket for rcv in self.receivers]
        if self.tcp_listener:
            sockets.extend(self.tcp_listener.sockets())
        if self.tcp_client and self.tcp_client.socket():
            sockets.append(self.tcp_client.socket())
        while True:
            now_mono = time.monotonic()
            self._prune_sent(now_mono)
            if self.tcp_client:
                self.tcp_client.ensure_connected()
                if self.tcp_client.socket() and self.tcp_client.socket() not in sockets:
                    sockets.append(self.tcp_client.socket())
            timeout = max(0.0, next_poll - time.monotonic())
            readable, _, _ = select.select(sockets, [], [], timeout)
            for sock in readable:
                if self.tcp_listener and sock is self.tcp_listener.server:
                    self.tcp_listener.accept_ready()
                    sockets = [rcv.socket for rcv in self.receivers]
                    sockets.extend(self.tcp_listener.sockets())
                    if self.tcp_client and self.tcp_client.socket():
                        sockets.append(self.tcp_client.socket())
                    continue
                if self.tcp_listener and self.tcp_listener.owns(sock):
                    for payload, addr in self.tcp_listener.recv_ready(sock):
                        self._handle_inbound(payload, addr)
                    continue
                if self.tcp_client and self.tcp_client.socket() is sock:
                    for payload, addr in self.tcp_client.recv_ready():
                        self._handle_inbound(payload, addr)
                    continue
                receiver = self.socket_map[sock.fileno()]
                payload, addr = receiver.recv()
                self._handle_inbound(payload, addr)

            now = time.monotonic()
            if now >= next_poll:
                self._flush_sigma()
                self._send_self_beacon(now)
                next_poll = now + self.config.poll_interval

    def _handle_inbound(self, payload: bytes, addr: tuple[str, int]) -> None:
        xml_text = payload.decode("utf-8", errors="replace")
        event = self.translator.parse_event(xml_text)
        raw_record = {
            "uid": event.unique_id,
            "callsign": None,
            "cot": event.event_type,
            "sidc": None,
            "source": f"{addr[0]}:{addr[1]}",
            "time": event.time.isoformat(),
            "stale": event.stale.isoformat(),
            "position": None,
            "detail": None,
            "raw_xml": xml_text,
        }
        sigma_payload = None
        try:
            sigma_payload = self.translator.event_to_sigma(event, addr)
            raw_record["callsign"] = sigma_payload.get("callsign")
            raw_record["sidc"] = sigma_payload.get("sidc")
            raw_record["position"] = sigma_payload.get("position")
            raw_record["detail"] = sigma_payload.get("detail")
        except Exception as exc:
            print(f"parse_error uid={event.unique_id} from={addr} reason={exc}")

        try:
            existing_raw = self.db.get(self.config.tak_db, "uid", event.unique_id)
            if existing_raw:
                self.db.update(self.config.tak_db, "uid", event.unique_id, raw_record)
            else:
                self.db.insert(self.config.tak_db, raw_record)
            print(f"tak_store uid={event.unique_id} cs={raw_record.get('callsign')} cot={event.event_type}")
        except Exception as exc:
            print(f"tak_db_write_failed uid={event.unique_id} reason={exc}")

        if self._is_loopback(event.unique_id):
            print(f"loopback_drop uid={event.unique_id}")
            return
        if sigma_payload is None:
            return
        self._upsert_sigma(sigma_payload)
        cs = sigma_payload.get("callsign") or ""
        print(f"inbound uid={event.unique_id} type={event.event_type} cs={cs} from={addr}")

    def _upsert_sigma(self, payload: dict) -> None:
        uid = payload["uid"]
        signature = (
            round(payload["position"]["lat"], 6),
            round(payload["position"]["lon"], 6),
            round(payload["position"]["alt"], 1),
            round(payload["position"]["ce"], 1),
            round(payload["position"]["le"], 1),
            payload.get("callsign"),
            payload.get("cot"),
        )
        now = time.monotonic()
        cached = self.last_writes.get(uid)
        if cached and cached[0] == signature and (now - cached[1]) < self.config.min_write_interval:
            #print(f"throttle uid={uid} db={self.config.sigma_push_db}")
            return
        existing = self.db.get(self.config.sigma_push_db, "uid", payload["uid"])
        if not existing and payload.get("unit_code") and payload["uid"] != payload["unit_code"]:
            existing = self.db.get(self.config.sigma_push_db, "unit_code", payload["unit_code"])
        if existing:
            self.db.update(self.config.sigma_push_db, "uid", payload["uid"], payload)
        else:
            self.db.insert(self.config.sigma_push_db, payload)
        self.last_writes[uid] = (signature, now)

    def _flush_sigma(self) -> None:
        for db_name in self.config.sigma_pull_dbs:
            records = self.db.get_all(db_name)
            for record in records:
                try:
                    xml_bytes = self.translator.sigma_to_event_xml(record)
                except ValueError as exc:
                    print(f"skip uid={record.get('uid') or record.get('unit_code')} db={db_name} reason={exc}")
                    continue
                self.sender.send(xml_bytes, self.config.targets)
                used_uid = record.get("uid") or record.get("unit_code")
                cs = record.get("callsign") or record.get("name") or record.get("unit_code") or record.get("uid") or ""
                #print(f"outbound uid={used_uid} cs={cs} db={db_name} targets={len(self.config.targets)}")
                self._record_sent(used_uid)
                if self.takserver_sender:
                    try:
                        self.takserver_sender.send(xml_bytes)
                        #print(f"outbound uid={used_uid} cs={cs} takserver={self.config.takserver.host}:{self.config.takserver.port}")
                        self._record_sent(used_uid)
                    except OSError as exc:
                        print(f"takserver send failed uid={used_uid} reason={exc}")

    def _record_sent(self, uid: str | None) -> None:
        if not uid:
            return
        self.sent_recent[uid] = time.monotonic()

    def _prune_sent(self, now: float) -> None:
        ttl = self.config.loopback_ttl
        expired = [k for k, ts in self.sent_recent.items() if now - ts > ttl]
        for k in expired:
            self.sent_recent.pop(k, None)

    def _is_loopback(self, uid: str | None) -> bool:
        if not uid:
            return False
        ts = self.sent_recent.get(uid)
        if ts is None:
            return False
        return (time.monotonic() - ts) <= self.config.loopback_ttl

    def _send_self_beacon(self, now: float) -> None:
        if not self.config.self_position or self.config.self_beacon_interval is None:
            return
        if now < self.next_self_beacon:
            return
        pos = self.config.self_position
        pos_payload = {
            "lat": pos["lat"],
            "lon": pos["lon"],
            "alt": pos.get("alt", 0.0),
            "ce": pos.get("ce", self.config.default_ce),
            "le": pos.get("le", self.config.default_le),
        }
        uid = self.self_uid
        xml_bytes = self.translator.client.cot_marker(
            self.config.self_callsign,
            uid,
            self.config.self_cottype,
            pos_payload,
            staletime=self.config.stale_seconds,
        )
        try:
            event = self.translator.parse_event(xml_bytes.decode("utf-8"))
            sigma_payload = self.translator.event_to_sigma(event, ("self", 0))
            self._upsert_sigma(sigma_payload)
        except Exception as exc:
            print(f"self_beacon_parse_failed uid={uid} reason={exc}")
        self.sender.send(xml_bytes, self.config.targets)
        self._record_sent(uid)
        if self.takserver_sender:
            try:
                self.takserver_sender.send(xml_bytes)
                self._record_sent(uid)
            except OSError as exc:
                print(f"takserver self send failed uid={uid} reason={exc}")
        self.next_self_beacon = now + self.config.self_beacon_interval


def parse_host_port(text: str) -> Endpoint:
    if ":" not in text:
        raise ValueError(f"Expected host:port, got '{text}'")
    host, port_str = text.rsplit(":", 1)
    return Endpoint(host=host, port=int(port_str))


def parse_args() -> AdapterConfig:
    parser = argparse.ArgumentParser(description="UDP CoT adapter for ATAK <-> Sigma (YAML config)")
    parser.add_argument("--config", required=True, help="Path to YAML config file")
    args = parser.parse_args()

    with open(args.config, "r", encoding="utf-8") as file:
        cfg = yaml.safe_load(file)

    if not isinstance(cfg, dict):
        raise ValueError("Config root must be a mapping")

    atak = cfg.get("atak")
    sigma = cfg.get("sigma")
    adapter_cfg = cfg.get("adapter")
    takserver_cfg = cfg.get("takserver")

    if not atak or not sigma or not adapter_cfg:
        raise ValueError("Config must include 'atak', 'sigma', and 'adapter' sections")

    listen_raw = atak.get("listen")
    targets_raw = atak.get("targets")
    if not listen_raw or not targets_raw:
        raise ValueError("atak.listen and atak.targets are required")
    if not isinstance(targets_raw, list):
        raise ValueError("atak.targets must be a list of host:port strings")

    listen = parse_host_port(listen_raw)
    multicast_raw = atak.get("multicast")
    multicast = parse_host_port(multicast_raw) if multicast_raw else None
    tcp_listen_raw = atak.get("tcp_listen")
    tcp_listen = parse_host_port(tcp_listen_raw) if tcp_listen_raw else None
    tak_tcp_raw = atak.get("tcp_connect")
    tak_tcp_connect = parse_host_port(tak_tcp_raw) if tak_tcp_raw else None
    targets = [parse_host_port(t) for t in targets_raw]

    sigma_base_url = sigma.get("base_url")
    sigma_push_db = sigma.get("push_db")
    sigma_pull_dbs = sigma.get("pull_dbs")
    if sigma_base_url is None or sigma_push_db is None or sigma_pull_dbs is None:
        raise ValueError("sigma.base_url, sigma.push_db, and sigma.pull_dbs are required (can be empty list)")
    if not isinstance(sigma_pull_dbs, list):
        raise ValueError("sigma.pull_dbs must be a list")

    poll_interval = adapter_cfg.get("poll_interval")
    stale_seconds = adapter_cfg.get("stale_seconds")
    default_ce = adapter_cfg.get("default_ce")
    default_le = adapter_cfg.get("default_le")
    self_callsign = adapter_cfg.get("self_callsign")
    self_cottype = adapter_cfg.get("self_cottype")
    min_write_interval = adapter_cfg.get("min_write_interval")
    loopback_ttl = adapter_cfg.get("loopback_ttl")
    tak_db = adapter_cfg.get("tak_db")
    self_position = adapter_cfg.get("self_position")
    self_beacon_interval = adapter_cfg.get("self_beacon_interval")
    self_uid = adapter_cfg.get("self_uid")

    missing = [k for k, v in {
        "poll_interval": poll_interval,
        "stale_seconds": stale_seconds,
        "default_ce": default_ce,
        "default_le": default_le,
        "self_callsign": self_callsign,
        "self_cottype": self_cottype,
        "min_write_interval": min_write_interval,
        "loopback_ttl": loopback_ttl,
        "tak_db": tak_db,
        "self_position": self_position,
        "self_beacon_interval": self_beacon_interval,
    }.items() if v is None]
    if missing:
        raise ValueError(f"Missing adapter fields: {', '.join(missing)}")
    if self_position is not None:
        if not isinstance(self_position, dict) or not all(k in self_position for k in ("lat", "lon", "alt")):
            raise ValueError("adapter.self_position must be a mapping with lat, lon, alt")
    if self_beacon_interval is not None and float(self_beacon_interval) <= 0:
        raise ValueError("adapter.self_beacon_interval must be > 0")

    takserver = None
    if takserver_cfg:
        host = takserver_cfg.get("host")
        port = takserver_cfg.get("port")
        if not host or port is None:
            raise ValueError("takserver.host and takserver.port are required when takserver block is present")
        takserver = Endpoint(host=host, port=int(port))

    config = AdapterConfig(
        listen=listen,
        multicast=multicast,
        tcp_listen=tcp_listen,
        tak_tcp_connect=tak_tcp_connect,
        targets=targets,
        takserver=takserver,
        sigma_base_url=sigma_base_url,
        sigma_auth_token=sigma.get("auth_token"),
        sigma_push_db=sigma_push_db,
        sigma_pull_dbs=sigma_pull_dbs,
        poll_interval=float(poll_interval),
        stale_seconds=int(stale_seconds),
        default_ce=float(default_ce),
        default_le=float(default_le),
        self_callsign=self_callsign,
        self_cottype=self_cottype,
        min_write_interval=float(min_write_interval),
        loopback_ttl=float(loopback_ttl),
        tak_db=str(tak_db),
        self_position={
            "lat": float(self_position["lat"]),
            "lon": float(self_position["lon"]),
            "alt": float(self_position["alt"]),
            **{k: float(self_position[k]) for k in ("ce", "le") if k in self_position},
        } if self_position is not None else None,
        self_uid=self_uid,
        self_beacon_interval=float(self_beacon_interval) if self_beacon_interval is not None else None,
    )
    return config


def main() -> None:
    config = parse_args()
    adapter = SigmaTakAdapter(config)
    adapter.run()


if __name__ == "__main__":
    main()
