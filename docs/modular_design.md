**Project: `upnp_cli_modular/`**

Below is a fully refactored, modular UPnP CLI skeleton.  Each section represents a separate file under `upnp_cli_modular/`.  Implementations are stubbed or illustrative; you can fill in internals as needed.

---

### Directory Structure

```
upnp_cli_modular/
├── __init__.py
├── cli.py
├── discovery_async.py
├── soap.py
├── cache.py
├── profiles/
│   └── sonos.yaml
├── utils.py
└── logging_config.py
```

---

### `__init__.py`

```python
# upnp_cli_modular/__init__.py
__version__ = "1.0.0"
```

---

### `logging_config.py`

```python
# upnp_cli_modular/logging_config.py
import logging
import sys

# Basic color formatter
class ColorFormatter(logging.Formatter):
    COLORS = {
        'DEBUG': '\u001b[37m',   # white
        'INFO': '\u001b[36m',    # cyan
        'WARNING': '\u001b[33m', # yellow
        'ERROR': '\u001b[31m',   # red
        'CRITICAL': '\u001b[41m',# red background
    }
    RESET = '\u001b[0m'

    def format(self, record):
        color = self.COLORS.get(record.levelname, self.RESET)
        message = super().format(record)
        return f"{color}{message}{self.RESET}"

# Configure root logger
def setup_logging(verbose: bool = False):
    level = logging.DEBUG if verbose else logging.INFO
    handler = logging.StreamHandler(sys.stdout)
    fmt = "%(asctime)s %(levelname)s: %(message)s"
    handler.setFormatter(ColorFormatter(fmt))
    root = logging.getLogger()
    root.setLevel(level)
    root.addHandler(handler)
```

---

### `utils.py`

```python
# upnp_cli_modular/utils.py
import socket
import netifaces
import subprocess
import ipaddress
from typing import Tuple, Optional, Any, List, Dict
import xml.etree.ElementTree as ET
import json

# 1) Get local IP / network

def get_en0_ip_and_network() -> Tuple[str, str]:
    """
    Return (IPv4 address on en0, network string in CIDR) or raise.
    """
    if 'en0' in netifaces.interfaces():
        addrs = netifaces.ifaddresses('en0')
        if netifaces.AF_INET in addrs:
            info = addrs[netifaces.AF_INET][0]
            ip = info['addr']
            netmask = info['netmask']
            network = ipaddress.IPv4Network(f"{ip}/{netmask}", strict=False)
            return ip, str(network)
    # fallback
    try:
        result = subprocess.run(['route', 'get', 'default'], capture_output=True, text=True)
        for line in result.stdout.splitlines():
            if 'gateway:' in line:
                # Not ideal; fallback to 127.0.0.1
                pass
    except:
        pass
    # fallback using UDP hack
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        network = ipaddress.IPv4Network(f"{ip}/24", strict=False)
        return ip, str(network)

# 2) YAML profile loader
def load_profiles(directory: str = None) -> List[Dict[str, Any]]:
    """Load all YAML profiles from `profiles/` folder."""
    import os, yaml
    profiles = []
    base = directory or os.path.join(os.path.dirname(__file__), 'profiles')
    for fname in os.listdir(base):
        if fname.endswith('.yaml') or fname.endswith('.yml'):
            path = os.path.join(base, fname)
            with open(path, 'r') as f:
                data = yaml.safe_load(f)
                profiles.append(data)
    return profiles

# 3) Parse UPnP device description XML and strip namespaces
def parse_device_description_xml(xml_text: str) -> Dict[str, Any]:
    """Return a dict of fields and service list."""
    root = ET.fromstring(xml_text)
    # Strip namespaces
    for elem in root.iter():
        if '}' in elem.tag:
            elem.tag = elem.tag.split('}', 1)[1]
    device = root.find('.//device')
    if device is None:
        raise ValueError("Invalid device description")
    info = {}
    for tag in ['deviceType', 'friendlyName', 'manufacturer', 'modelName',
               'modelNumber', 'softwareVersion', 'serialNum', 'UDN']:
        el = device.find(tag)
        if el is not None:
            info[tag] = el.text
    # collect services
    services = []
    sl = device.find('serviceList')
    if sl is not None:
        for svc in sl.findall('service'):
            svcinfo = {}
            for f in ['serviceType', 'serviceId', 'controlURL', 'eventSubURL', 'SCPDURL']:
                el = svc.find(f)
                if el is not None:
                    svcinfo[f] = el.text
            services.append(svcinfo)
    info['services'] = services
    return info

# 4) Cache utilities (stubbed)
```

---

### `cache.py`

```python
# upnp_cli_modular/cache.py
import sqlite3
import json
import time
from pathlib import Path
from typing import Optional, Dict, Any, List

DB_PATH = Path.home() / '.upnp_cli' / 'devices_cache.db'
TABLE = 'device_cache'

class Cache:
    def __init__(self, path: Path = DB_PATH):
        self.path = path
        self._ensure_table()

    def _ensure_table(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.path)
        c = conn.cursor()
        c.execute(f'''
            CREATE TABLE IF NOT EXISTS {TABLE} (
                ip TEXT PRIMARY KEY,
                port INTEGER,
                last_seen REAL,
                data TEXT
            )''')
        conn.commit()
        conn.close()

    def upsert(self, ip: str, port: int, info: Dict[str, Any]):
        ts = time.time()
        data = json.dumps(info)
        conn = sqlite3.connect(self.path)
        c = conn.cursor()
        c.execute(f'''
            INSERT INTO {TABLE} (ip, port, last_seen, data)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(ip) DO UPDATE SET
              port=excluded.port,
              last_seen=excluded.last_seen,
              data=excluded.data;''', (ip, port, ts, data))
        conn.commit()
        conn.close()

    def get(self, ip: str) -> Optional[Dict[str, Any]]:
        conn = sqlite3.connect(self.path)
        c = conn.cursor()
        c.execute(f"SELECT port, last_seen, data FROM {TABLE} WHERE ip = ?", (ip,))
        row = c.fetchone()
        conn.close()
        if not row:
            return None
        port, last_seen, data = row
        return { 'ip': ip, 'port': port, 'last_seen': last_seen, 'info': json.loads(data) }

    def list(self, max_age: float = 24*3600) -> List[Dict[str, Any]]:
        cutoff = time.time() - max_age
        conn = sqlite3.connect(self.path)
        c = conn.cursor()
        c.execute(f"SELECT ip, port, last_seen, data FROM {TABLE} WHERE last_seen >= ?", (cutoff,))
        rows = c.fetchall()
        conn.close()
        out = []
        for ip, port, last, data in rows:
            out.append({ 'ip': ip, 'port': port, 'last_seen': last, 'info': json.loads(data) })
        return out
```

---

### `discovery_async.py`

```python
# upnp_cli_modular/discovery_async.py
import asyncio
import aiohttp
import logging
from typing import List, Dict, Any
from .utils import parse_device_description_xml, get_en0_ip_and_network

logger = logging.getLogger(__name__)

SSDP_MULTICAST = ('239.255.255.250', 1900)

SSDP_MX = 3

SSDP_HEADERS = '\r\n'.join([
    'M-SEARCH * HTTP/1.1',
    'HOST: 239.255.255.250:1900',
    'MAN: "ssdp:discover"',
    'ST: upnp:rootdevice',
    f'MX: {SSDP_MX}',
    '',
    ''
]).encode('utf-8')

async def _send_ssdp(loop: asyncio.AbstractEventLoop, responses: List[Dict[str, Any]]):
    """Send one SSDP M-SEARCH and collect all replies for SSDP_MX seconds."""
    transport, protocol = await loop.create_datagram_endpoint(
        lambda: SSDPClientProtocol(responses),
        family=asyncio.socket.AF_INET,
        proto=asyncio.socket.IPPROTO_UDP)

    transport.sendto(SSDP_HEADERS, SSDP_MULTICAST)
    await asyncio.sleep(SSDP_MX)
    transport.close()

class SSDPClientProtocol:
    def __init__(self, responses: List[Dict[str, Any]]):
        self.responses = responses

    def connection_made(self, transport):
        pass

    def datagram_received(self, data: bytes, addr):
        try:
            text = data.decode('utf-8', errors='ignore')
            headers = {}
            for line in text.split('\r\n'):
                if ':' in line:
                    key, val = line.split(':', 1)
                    headers[key.upper()] = val.strip()
            location = headers.get('LOCATION')
            if location:
                self.responses.append({ 'location': location, 'addr': addr })
        except:
            pass

    def error_received(self, exc):
        logger.warning(f"SSDP error_received: {exc}")

    def connection_lost(self, exc):
        pass

async def discover_upnp_devices(timeout: int = 5) -> List[Dict[str, Any]]:
    """Run SSDP discovery and fetch each device description asynchronously."""
    loop = asyncio.get_event_loop()
    responses: List[Dict[str, Any]] = []
    await _send_ssdp(loop, responses)

    devices: List[Dict[str, Any]] = []
    async with aiohttp.ClientSession() as session:
        tasks = []
        for resp in responses:
            location = resp['location']
            tasks.append(fetch_device_description(session, location))
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for result in results:
            if isinstance(result, dict):
                devices.append(result)
    return devices

async def fetch_device_description(session: aiohttp.ClientSession, location: str) -> Dict[str, Any]:
    """Fetch and parse a single device_description.xml from a UPnP device."""
    try:
        async with session.get(location, timeout=5) as resp:
            if resp.status == 200:
                text = await resp.text()
                info = parse_device_description_xml(text)
                parsed = aiohttp.helpers.URL(location)
                info['ip'] = parsed.host
                info['port'] = parsed.port or 80
                return info
    except Exception as e:
        logging.getLogger(__name__).warning(f"Failed to fetch {location}: {e}")
    return {}
```

---

### `soap.py`

```python
# upnp_cli_modular/soap.py
import asyncio
import aiohttp
import xml.etree.ElementTree as ET
import logging

logger = logging.getLogger(__name__)

async def send_soap_request(session: aiohttp.ClientSession, host: str, port: int,
                            control_url: str, service_type: str, action: str,
                            arguments: dict, use_ssl: bool = False,
                            timeout: int = 10) -> aiohttp.ClientResponse:
    """Send a single SOAP request asynchronously."""
    proto = 'https' if use_ssl else 'http'
    url = f"{proto}://{host}:{port}{control_url}"
    envelope = build_soap_envelope(service_type, action, arguments)
    headers = {
        'Content-Type': 'text/xml; charset="utf-8"',
        'SOAPAction': f'"{service_type}#{action}"'
    }
    try:
        async with session.post(url, data=envelope.encode('utf-8'), headers=headers, timeout=timeout) as resp:
            return resp
    except Exception as e:
        logger.error(f"SOAP request to {url} failed: {e}")
        raise


def build_soap_envelope(service_type: str, action: str, arguments: dict) -> str:
    """Construct a minimal SOAP envelope."""
    envelope = ET.Element("s:Envelope", {
        "xmlns:s": "http://schemas.xmlsoap.org/soap/envelope/",
        "s:encodingStyle": "http://schemas.xmlsoap.org/soap/encoding/"
    })
    body = ET.SubElement(envelope, "s:Body")
    u = ET.SubElement(body, f"u:{action}", {"xmlns:u": service_type})
    for arg, val in arguments.items():
        el = ET.SubElement(u, arg)
        el.text = str(val)
    xml = ET.tostring(envelope, encoding='utf-8', xml_declaration=True)
    return xml.decode('utf-8')

async def parse_soap_response(resp: aiohttp.ClientResponse, verbose: bool = False) -> str:
    """Parse response and return concise or verbose info."""
    text = await resp.text()
    code = resp.status
    if verbose:
        headers = '\n'.join([f"{k}: {v}" for k, v in resp.headers.items()])
        snippet = text if len(text) < 1000 else text[:1000] + '…(truncated)…'
        return f"HTTP {code}\nHeaders:\n{headers}\n\nBody:\n{snippet}"
    else:
        snippet = text if len(text) < 300 else text[:300] + '…(truncated)…'
        return f"HTTP {code}\n{snippet}"
```

---

### `cli.py`

```python
# upnp_cli_modular/cli.py
import argparse
import sys
import asyncio
import json
import logging

from .logging_config import setup_logging
from .discovery_async import discover_upnp_devices
from .soap import send_soap_request, parse_soap_response
from .utils import get_en0_ip_and_network, load_profiles
from .cache import Cache

logger = logging.getLogger(__name__)

async def cmd_discover(args):
    print("🔍 Discovering UPnP devices… (this may take a few seconds)")
    devices = await discover_upnp_devices(timeout=5)
    # Update cache
    cache = Cache()
    for dev in devices:
        ip = dev['ip']
        port = dev['port']
        cache.upsert(ip, port, dev)
    print(json.dumps(devices, indent=2))

async def cmd_info(args):
    cache = Cache()
    if args.host:
        entry = cache.get(args.host)
        if entry:
            print(json.dumps(entry['info'], indent=2))
            return
    print("No cached info for that host; try `discover` first.")

async def cmd_get_volume(args):
    host = args.host
    port = args.port
    use_ssl = args.use_ssl
    async with aiohttp.ClientSession() as session:
        resp = await send_soap_request(session, host, port,
                                       "/MediaRenderer/RenderingControl/Control",
                                       "urn:schemas-upnp-org:service:RenderingControl:1",
                                       "GetVolume", {"InstanceID": 0, "Channel": "Master"},
                                       use_ssl=use_ssl)
        out = await parse_soap_response(resp, args.verbose)
        print(out)

async def main():
    parser = argparse.ArgumentParser(prog="upnp-cli", description="Modular UPnP CLI tool")
    parser.add_argument("--host", help="Target IP (optional for discover)")
    parser.add_argument("--port", type=int, default=1400, help="Default UPnP port")
    parser.add_argument("--ssl-port", type=int, default=1443)
    parser.add_argument("--use-ssl", action="store_true")
    parser.add_argument("--verbose", "-v", action="store_true")
    parser.add_argument("--cache", action="store_true", help="Use cache for host info if available")
    sub = parser.add_subparsers(dest="cmd")

    sub.add_parser("discover", help="Discover all UPnP devices")
    sub.add_parser("info", help="Show cached device info for --host")
    sub_vol = sub.add_parser("get-volume", help="Get current volume")
    # (add other subcommands similarly…)

    args = parser.parse_args()
    setup_logging(args.verbose)

    if not args.cmd:
        parser.print_help()
        sys.exit(0)

    if args.cmd == "discover":
        await cmd_discover(args)
    elif args.cmd == "info":
        await cmd_info(args)
    elif args.cmd == "get-volume":
        await cmd_get_volume(args)
    else:
        logger.error(f"Unknown command: {args.cmd}")
        sys.exit(1)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(0)
```

---

### `profiles/sonos.yaml`

```yaml
manufacturer: "Sonos, Inc."
deviceTypeContains:
  - "ZonePlayer"
  - "ZonePlayerEx"
default_ports:
  - 1400
  - 1443
services:
  - name: "AVTransport"
    serviceType: "urn:schemas-upnp-org:service:AVTransport:1"
    controlURL: "/MediaRenderer/AVTransport/Control"
  - name: "RenderingControl"
    serviceType: "urn:schemas-upnp-org:service:RenderingControl:1"
    controlURL: "/MediaRenderer/RenderingControl/Control"
  - name: "GroupRenderingControl"
    serviceType: "urn:schemas-upnp-org:service:GroupRenderingControl:1"
    controlURL: "/MediaRenderer/GroupRenderingControl/Control"
  - name: "Queue"
    serviceType: "urn:schemas-sonos-com:service:Queue:1"
    controlURL: "/MediaRenderer/Queue/Control"
quirks:
  - always_use_queue_for_uri
  - repeat_all_before_play
```

---

#### How to Use

1. **Install dependencies** (assuming you publish to PyPI or clone locally):

   ```bash
   pip install aiohttp pyyaml netifaces
   ```
2. **Run discovery**:

   ```bash
   upnp-cli discover
   ```
3. **Get volume** (after discovery caches a device)

   ```bash
   upnp-cli --host 192.168.4.152 get-volume
   ```
4. **Use `--cache`** to bypass SSDP on repeated runs:

   ```bash
   upnp-cli --cache info --host 192.168.4.152
   ```

> **Note:** This skeleton shows how to split logic into separate modules (`discovery_async.py`, `soap.py`, `cache.py`, etc.), introduce YAML-based profiles under `profiles/`, and wire everything together in `cli.py` with proper async I/O, logging, and caching. Feel free to expand on each stub—implement full SOAP‐to‐action mappings, error handling, and “fart-loop” prank functions as needed.
