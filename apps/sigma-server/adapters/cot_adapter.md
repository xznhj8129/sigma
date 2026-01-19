# Cursor-on-Target UDP adapter

Adapter for exchanging CoT messages between ATAK and Sigma over UDP (unicast or multicast). It ingests ATAK datagrams, converts them with `frogcot`, stores them in Sigma DB, and periodically exports Sigma units/tracks back to ATAK as CoT markers.

## Dependencies
- Install Sigma server deps: `pip install -r apps/sigma-server/requirements.txt`
- Install `frogcot` from the sibling repo: `pip install -e /media/anon/WD2TB/DataVault/TechProjects/Software/GitRepos/frogcot`
- Sigma DB must be running and reachable at the `sigma.base_url` provided.

## Config (YAML)
Example: `apps/sigma-server/adapters/cot_adapter.sample.yml`
```yaml
atak:
  listen: "0.0.0.0:4242"
  multicast: "239.2.3.1:4242"
  tcp_listen: "0.0.0.0:8087"
  tcp_connect: "192.168.0.213:8087"
  targets:
    - "239.2.3.1:4242"
    - "127.0.0.1:8087"
sigma:
  base_url: "http://127.0.0.1:5001/api"
  auth_token: null
  push_db: "intel"
  pull_dbs: []
adapter:
  poll_interval: 2.0
  stale_seconds: 60
  default_ce: 50.0
  default_le: 50.0
  self_callsign: "SIGMA"
  self_cottype: "a-f-U"
  min_write_interval: 1.5
  loopback_ttl: 5.0
  tak_db: "tak"
  self_position:
    lat: 36.530310
    lon: -83.21722
    alt: 0.0
    ce: 25.0
    le: 25.0
  self_beacon_interval: 30.0
  self_uid: "SIGMA-HUB"
takserver:
  host: "127.0.0.1"
  port: 8087
```

## Run
```bash
python apps/sigma-server/adapters/cot_adapter.py --config apps/sigma-server/adapters/cot_adapter.sample.yml
```

## Behaviour
- Listens on the unicast socket given by `--atak-listen`; joins `--atak-multicast` if supplied.
- Received CoT XML is parsed with `frogcot.xml_to_cot` (with a relaxed fallback for version `2.0` payloads) and upserted into the Sigma DB collection given by `--sigma-push-db` using `uid` as the key.
- Every `--poll-interval` seconds, fetches all documents from each `--sigma-pull-db` and emits CoT markers to every `--atak-target`.
- If `takserver` is provided, the same outbound CoT is also sent over TCP to that TAK server endpoint.
- CoT type resolution prefers `record["cot"]`, otherwise converts `sidc` via `frogcot.convert_2525b_to_cot`. Missing `cot` and `sidc` causes the record to be skipped.
- Position requires `lat`, `lon`, and `alt`; `ce`/`le` fall back to the provided `--default-ce`/`--default-le`.
- Adapter identity for outbound markers is set by `--self-callsign` and `--self-cottype`.
- Inbound writes are throttled per `uid` when position/callsign/type are unchanged within `adapter.min_write_interval` seconds.
- Loopback guard drops any inbound packet whose `uid` was sent by this adapter in the last `adapter.loopback_ttl` seconds (prevents Sigma->ATAK->Sigma echo).
- Inbound CoT is also stored verbatim (with parsed fields) into `adapter.tak_db` for later handling by affiliation/type.
- Self beacon: if `adapter.self_position` and `adapter.self_beacon_interval` are provided, the adapter emits its own CoT marker (callsign/uid from config) on that interval to ATAK and upserts it into the push DB.
- Optional TCP ingest: set `atak.tcp_listen` to receive CoT over TCP (e.g., from Meshtastic forwarders); UDP ingest stays enabled.
- Optional TAK TCP client: set `atak.tcp_connect` to connect to an existing TAK server (e.g., taky) and ingest its CoT feed.
- Stdout logs each inbound/outbound packet with `uid`, event type, and target count.

## Conversion notes
- Contact callsign is pulled from CoT `<contact callsign="...">` if present.
- SIDC conversion only covers patterns supported by `frogcot`; anything else is ignored.
- Stale time per marker defaults to `--stale-seconds` unless the record includes `stale_seconds`.
- The adapter assumes DB documents include `uid`, `position`, and either `cot` or `sidc`; missing fields trigger a skip with a printed reason.
