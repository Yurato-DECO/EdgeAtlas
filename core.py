"""Trace collection and approximate edge-city coordinates. No GUI dependencies."""
from dataclasses import dataclass, field, asdict
from datetime import datetime
from urllib.parse import urlsplit, urlunsplit
from concurrent.futures import ThreadPoolExecutor, as_completed
import re
import time
import requests

# Approximate city centers, NOT exact Cloudflare facility locations.
_CITIES = """
ICN|Seoul / Incheon|KR|37.4563|126.7052
NRT|Tokyo|JP|35.6762|139.6503
HND|Tokyo|JP|35.6762|139.6503
KIX|Osaka|JP|34.6937|135.5023
FUK|Fukuoka|JP|33.5904|130.4017
TPE|Taipei|TW|25.0330|121.5654
HKG|Hong Kong|HK|22.3193|114.1694
SIN|Singapore|SG|1.3521|103.8198
MNL|Manila|PH|14.5995|120.9842
BKK|Bangkok|TH|13.7563|100.5018
KUL|Kuala Lumpur|MY|3.1390|101.6869
CGK|Jakarta|ID|-6.2088|106.8456
SGN|Ho Chi Minh City|VN|10.8231|106.6297
HAN|Hanoi|VN|21.0278|105.8342
BOM|Mumbai|IN|19.0760|72.8777
DEL|New Delhi|IN|28.6139|77.2090
MAA|Chennai|IN|13.0827|80.2707
SYD|Sydney|AU|-33.8688|151.2093
MEL|Melbourne|AU|-37.8136|144.9631
AKL|Auckland|NZ|-36.8485|174.7633
LAX|Los Angeles|US|34.0522|-118.2437
SJC|San Jose|US|37.3382|-121.8863
SFO|San Francisco|US|37.7749|-122.4194
SEA|Seattle|US|47.6062|-122.3321
PDX|Portland|US|45.5152|-122.6784
DFW|Dallas|US|32.7767|-96.7970
ORD|Chicago|US|41.8781|-87.6298
IAD|Ashburn|US|39.0438|-77.4874
EWR|Newark|US|40.7357|-74.1724
JFK|New York|US|40.7128|-74.0060
BOS|Boston|US|42.3601|-71.0589
ATL|Atlanta|US|33.7490|-84.3880
MIA|Miami|US|25.7617|-80.1918
YYZ|Toronto|CA|43.6532|-79.3832
YVR|Vancouver|CA|49.2827|-123.1207
LHR|London|GB|51.5074|-0.1278
AMS|Amsterdam|NL|52.3676|4.9041
FRA|Frankfurt|DE|50.1109|8.6821
CDG|Paris|FR|48.8566|2.3522
MAD|Madrid|ES|40.4168|-3.7038
WAW|Warsaw|PL|52.2297|21.0122
ARN|Stockholm|SE|59.3293|18.0686
DXB|Dubai|AE|25.2048|55.2708
JNB|Johannesburg|ZA|-26.2041|28.0473
GRU|Sao Paulo|BR|-23.5505|-46.6333
SCL|Santiago|CL|-33.4489|-70.6693
"""

def bundled_locations():
    result = {}
    for line in _CITIES.strip().splitlines():
        code, city, country, lat, lon = line.split('|')
        result[code] = dict(city=city, country=country, lat=float(lat), lon=float(lon))
    return result

def fetch_locations():
    locations = bundled_locations()
    try:
        response = requests.get('https://speed.cloudflare.com/locations', timeout=(3, 5))
        response.raise_for_status()
        for item in response.json():
            code = str(item['iata']).upper()
            lat, lon = float(item['lat']), float(item['lon'])
            if re.fullmatch(r'[A-Z]{3}', code) and -90 <= lat <= 90 and -180 <= lon <= 180:
                locations[code] = dict(city=str(item['city']), country=str(item.get('cca2', '')), lat=lat, lon=lon)
        return locations, 'Cloudflare 위치 목록 + 기본 도시 좌표'
    except (requests.RequestException, ValueError, KeyError, TypeError):
        return locations, '기본 도시 좌표 사용 · 위치 목록을 받지 못했습니다'

def trace_url(value):
    value = value.strip()
    if not value or any(c.isspace() for c in value):
        raise ValueError('공백 없는 도메인 또는 URL을 입력하세요.')
    parsed = urlsplit(value if '://' in value else 'https://' + value)
    if parsed.scheme not in ('http', 'https') or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError('http/https 도메인만 지원하며 로그인 정보는 넣을 수 없습니다.')
    try:
        host = parsed.hostname.encode('idna').decode('ascii')
        port = parsed.port
    except (ValueError, UnicodeError) as exc:
        raise ValueError('잘못된 호스트 또는 포트입니다.') from exc
    host = '[' + host + ']' if ':' in host else host
    netloc = host + (f':{port}' if port is not None else '')
    return urlunsplit((parsed.scheme, netloc, '/cdn-cgi/trace', '', ''))

def parse_trace(body):
    if len(body) > 65536 or '<html' in body.lower():
        raise ValueError('trace 대신 웹페이지 또는 너무 큰 응답을 받았습니다.')
    fields = dict(line.split('=', 1) for line in body.splitlines() if '=' in line)
    if not re.fullmatch(r'[A-Z]{3}', fields.get('colo', '')) or not fields.get('ip'):
        raise ValueError('유효한 Cloudflare trace가 없습니다. 미지원 사이트 또는 차단 응답일 수 있습니다.')
    return fields

@dataclass
class TraceResult:
    site: str
    url: str = ''
    colo: str = ''
    elapsed_ms: float = 0
    timestamp: str = ''
    fields: dict = field(default_factory=dict)
    error: str = ''

    def to_dict(self):
        return asdict(self)

def probe(site, timeout=10, session=None):
    result = TraceResult(site=site, timestamp=datetime.now().astimezone().isoformat(timespec='seconds'))
    started = time.monotonic()
    try:
        result.url = trace_url(site)
        client = session or requests
        # Redirects are deliberately visible: don't attribute another host's colo to this site.
        with client.get(result.url, timeout=(timeout, timeout), allow_redirects=False, stream=True,
                        headers={'User-Agent': 'EdgeAtlas/1.0', 'Cache-Control': 'no-cache'}) as response:
            if 300 <= response.status_code < 400:
                raise ValueError('리디렉션 응답입니다. 실제 대상 도메인을 입력하세요.')
            response.raise_for_status()
            chunks, size = [], 0
            for chunk in response.iter_content(4096):
                size += len(chunk)
                if size > 65536 or time.monotonic() - started > timeout * 2:
                    raise ValueError('응답 크기 또는 수신 시간 제한을 초과했습니다.')
                chunks.append(chunk)
            result.fields = parse_trace(b''.join(chunks).decode('utf-8', errors='replace'))
            result.colo = result.fields['colo']
    except (ValueError, requests.RequestException) as exc:
        result.error = str(exc)
    result.elapsed_ms = round((time.monotonic() - started) * 1000, 1)
    return result

def probe_many(sites, cancelled):
    if cancelled.is_set():
        return
    with ThreadPoolExecutor(max_workers=6) as pool:
        pending = {pool.submit(probe, site): site for site in sites}
        for future in as_completed(pending):
            if cancelled.is_set():
                for task in pending:
                    task.cancel()
                break
            yield future.result()
