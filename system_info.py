"""Read-only device/network information, collected off the GUI thread."""
import ipaddress
import json
import os
import platform
import subprocess
from PySide6.QtCore import QThread, Signal
from core import probe


def os_description():
    name = platform.system()
    release = platform.release()
    version = platform.version()
    machine = platform.machine()
    architecture = '64비트' if machine.upper() in ('AMD64', 'X86_64', 'ARM64', 'AARCH64') else machine
    return f'{name} {release} · {architecture}', f'{name} {release}\n버전 {version}\n아키텍처 {machine}'


def configured_dns():
    """DNS configured on the lowest-metric default interface per IP family."""
    if os.name != 'nt':
        return '지원하지 않는 OS', 'DNS 어댑터 조회는 Windows에서 지원합니다.'
    script = r'''
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$routes = @(Get-NetRoute -ErrorAction Stop | Where-Object {
    $_.DestinationPrefix -eq '0.0.0.0/0' -or $_.DestinationPrefix -eq '::/0'
})
$selected = @($routes | Group-Object AddressFamily | ForEach-Object {
    $_.Group | Sort-Object @{ Expression = { $_.RouteMetric + $_.InterfaceMetric } } | Select-Object -First 1
} | Select-Object -ExpandProperty InterfaceIndex -Unique)
$result = @(foreach ($index in $selected) {
    Get-DnsClientServerAddress -InterfaceIndex $index -ErrorAction Stop | ForEach-Object {
        if ($_.ServerAddresses.Count -gt 0) {
            [PSCustomObject]@{ adapter = $_.InterfaceAlias; servers = @($_.ServerAddresses) }
        }
    }
})
ConvertTo-Json -InputObject $result -Compress -Depth 4
'''
    try:
        result = subprocess.run(
            ['powershell.exe', '-NoProfile', '-NonInteractive', '-Command', script],
            capture_output=True, encoding='utf-8', errors='replace', timeout=12,
            creationflags=subprocess.CREATE_NO_WINDOW, check=True)
        rows = json.loads(result.stdout.lstrip('\ufeff').strip())
        servers, details = [], []
        for row in rows:
            valid = [str(ipaddress.ip_address(value)) for value in row['servers']]
            servers.extend(value for value in valid if value not in servers)
            if valid:
                details.append(str(row['adapter']) + ': ' + ', '.join(valid))
        if not servers:
            return '설정 정보 없음', '기본 경로의 네트워크 어댑터에서 DNS 주소를 찾지 못했습니다.'
        return '\n'.join(servers), '\n'.join(details) + '\nWindows에 설정된 DNS입니다. 브라우저 보안 DNS와 다를 수 있습니다.'
    except (subprocess.SubprocessError, OSError, ValueError, KeyError, TypeError):
        return '조회 실패', 'Windows 네트워크 설정을 읽지 못했습니다. 정보 새로고침으로 다시 조회할 수 있습니다.'


class SystemInfoWorker(QThread):
    info = Signal(str, str, str)

    def run(self):
        # Public IP is the egress address Cloudflare observes for this request.
        result = probe('https://www.cloudflare.com', timeout=4)
        try:
            address = str(ipaddress.ip_address(result.fields.get('ip', '')))
            self.info.emit('ip', address, 'Cloudflare가 관측한 이 요청의 공인 IP입니다. VPN/프록시 사용 시 해당 출구 IP가 표시됩니다.')
        except ValueError:
            self.info.emit('ip', '조회 실패', '공인 IP를 확인하지 못했습니다. 정보 새로고침으로 다시 조회할 수 있습니다.')
        value, detail = configured_dns()
        self.info.emit('dns', value, detail)
