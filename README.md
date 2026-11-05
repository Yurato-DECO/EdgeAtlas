# Edge Atlas — Cloudflare 접속 지도

Python GUI에서 여러 사이트의 `/cdn-cgi/trace`를 요청하고, `colo`에 해당하는 Cloudflare 접속 도시를 **OpenStreetMap** 위에 표시합니다. API 키는 필요 없습니다.

화면에는 Material Design 3의 색상 역할, 둥근 카드, Filled/Tonal/Outlined 버튼, 상태 칩, 애니메이션 스위치와 키보드 포커스 표시를 Qt Widgets로 구현했습니다. 공식 Material 컴포넌트 라이브러리를 사용하는 것은 아닙니다. 색상과 컴포넌트 스타일은 `material_ui.py`에 모았습니다.

앱과 지도 오버레이의 글꼴은 **나눔고딕**입니다. Regular/Bold 폰트를 앱에 포함하므로 Windows에 별도로 설치하거나 외부 폰트 서버에 연결할 필요가 없습니다. 지도 타일에 원래 그려진 지명 글씨는 OSM 제공 이미지의 일부입니다. 폰트의 SIL OFL 라이선스는 `assets/fonts/nanum-gothic/OFL.txt`에 포함되어 있습니다.

## 실행

### Windows EXE 배포판

`EdgeAtlas-Windows-x64.zip`을 **전체 압축 해제**한 뒤 `EdgeAtlas/EdgeAtlas.exe`를 실행합니다. Python을 설치할 필요가 없습니다. EXE 옆의 `_internal` 폴더도 함께 유지해야 합니다. 실행 시 큰 라이브러리를 매번 압축 해제하지 않도록 폴더형으로 패키징했습니다. 지도와 사이트 측정에는 인터넷 연결이 필요합니다.

파일·창·작업표시줄 아이콘에는 프로젝트 루트의 `icon.png`를 사용합니다.

개발 환경에서 다시 빌드하려면 `build.bat`를 실행하세요. 결과는 `dist/EdgeAtlas/EdgeAtlas.exe`입니다. 배포에는 `dist/EdgeAtlas` 폴더 전체를 사용하세요. PyInstaller 설정은 `EdgeAtlas.spec`, 빌드 도구 버전은 `requirements-build.txt`에서 관리합니다.

### Python 소스 실행

Windows에서 **`run.bat`를 더블클릭**하세요. 처음에는 가상환경과 의존성을 설치합니다. Python 3.10 이상과 인터넷 연결이 필요합니다. 이 작업 환경에서는 Python 3.14로 설치했습니다.

직접 실행하려면:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe app.py
```

## 사용법

1. 왼쪽 입력란에 도메인 또는 URL을 한 줄에 하나씩 입력합니다.
2. **측정 시작**을 누릅니다. 기본 출발점은 서울이며 이름과 위도·경도를 바꿀 수 있습니다.
3. 지도에서 출발점과 접속 도시를 잇는 선을 확인합니다. 점이나 선에 마우스를 올리면 사이트 목록이 나옵니다.
4. 결과 행을 선택하면 해당 연결을 강조하고 trace 필드 또는 오류를 표시합니다.
5. **자동 재측정** 글자 또는 스위치를 누르면 즉시 첫 측정을 시작합니다. 이후 측정 완료 시점부터 설정한 간격으로 반복하며, `다음 측정까지 N초`를 표시합니다. 실행 중에 켜면 현재 측정을 마친 뒤 반복합니다. 대기 중에도 **중지**를 누르거나 스위치를 끄면 다음 측정을 취소합니다. 이전 성공 측정과 지역이 달라지면 `ICN → NRT`처럼 표시합니다.
6. **결과 CSV 저장**으로 현재 결과를 UTF-8 BOM CSV로 저장합니다.
7. 좌측 하단 **내 네트워크**에서 공인 IP, DNS, OS를 확인합니다. 새로고침 버튼으로 네트워크 정보를 다시 읽을 수 있습니다. 설정 영역을 스크롤해도 이 정보는 하단에 유지됩니다.

## 해석할 때 알아둘 점

- `colo=ICN`은 해당 HTTP 요청을 처리한 Cloudflare 접속 지점의 코드입니다. `loc=KR`은 클라이언트 국가 코드이며 서버 위치가 아닙니다.
- 선은 두 위치를 연결한 개념도입니다. 실제 중간 라우터, 해저 케이블, Cloudflare 내부 경로, 원본 서버의 위치를 알아내는 기능은 아닙니다.
- 좌표는 도시 수준의 근사치입니다. 출발점은 사용자가 지정한 위치이며 자동 IP 위치 추적이 아닙니다.
- 시작 후 첫 측정에서 Cloudflare 공개 위치 목록을 요청합니다. 실패하면 내장된 46개 주요 코드 좌표를 사용합니다. 미등록 코드는 결과 표에 표시하고 지도에서는 생략합니다. 이 공개 목록의 지속적인 제공은 보장되지 않습니다.
- HTTP 소요 시간은 DNS, 연결, TLS, 응답 전송 등을 포함하며 ICMP ping이 아닙니다. VPN/프록시, 네트워크와 요청 시점에 따라 결과가 달라질 수 있습니다. Python requests의 HTTP 요청이며 브라우저의 HTTP/3 연결과 결과가 다를 수 있습니다.
- Cloudflare를 사용하는 사이트라도 trace가 차단되거나 제공되지 않을 수 있습니다. 리디렉션은 다른 도메인의 결과로 오인하지 않도록 따라가지 않습니다. 실제 대상 도메인을 직접 입력하세요.
- 최소 자동 간격은 15초, 최대 사이트는 100개, 동시 요청은 6개입니다. 중지 시 이미 진행 중인 요청 정리를 기다립니다.

## 데이터와 지도

- 공인 IP는 앱 시작/정보 새로고침 시 Cloudflare trace로 확인하며 VPN/프록시 사용 시 해당 요청의 출구 IP를 표시합니다. DNS는 IPv4/IPv6 기본 경로 중 우선순위가 높은 어댑터의 Windows 설정값입니다. 브라우저 보안 DNS, 도메인별 DNS 정책, DNS 프록시의 상위 서버와는 다를 수 있습니다. 조회는 백그라운드에서 수행하며 IP/DNS를 파일로 저장하지 않습니다.

- 사이트와 출발점 설정은 Windows 사용자 설정(`HKEY_CURRENT_USER\Software\EdgeAtlas\EdgeAtlas`)에 저장합니다. 측정 결과는 CSV로 저장하기 전까지 메모리에만 유지합니다.
- trace 원문에는 공인 IP가 포함될 수 있으며 하단 상세 창에 표시합니다. CSV 및 지도 데이터에서는 공인 IP를 제외합니다.
- Leaflet 1.9.4 스크립트/CSS/이미지는 앱의 `vendor/leaflet-1.9.4`에 포함되어 실행 시 외부 CDN 연결을 기다리지 않습니다. 원본 라이선스는 같은 폴더의 `LICENSE`입니다. 배경 지도 타일은 tile.openstreetmap.org에서 받으며 해당 서버에는 일반적인 웹 요청 정보가 전달됩니다.
- 지도 타일은 QtWebEngine 전용 프로필에서 서버의 HTTP 캐시 정책에 따라 캐시합니다. 앱 식별 User-Agent를 전송합니다.
- 첫 화면의 불필요한 세계 지도 요청과 확대/페이드 애니메이션을 없앴습니다. 연속 측정 결과의 지도 갱신은 60ms 단위로 합칩니다. 처음 보는 지역의 타일 속도는 네트워크와 OSM 서버 응답에 따라 달라집니다.
- 지도 문서는 127.0.0.1의 로컬 전용 임의 경로로 제공합니다. 실행할 때마다 OS가 빈 포트를 선택하여 여러 창을 실행해도 서로 다른 지도 서버에 연결합니다.
- OpenStreetMap 출처 표시는 지도에 유지합니다. 타일을 대량 다운로드하거나 오프라인 저장하지 않습니다.

## 검증

```powershell
.\.venv\Scripts\python.exe -m unittest -v test_core
.\.venv\Scripts\python.exe -m unittest -v test_auto_refresh
.\.venv\Scripts\python.exe smoke_gui.py
```

첫 명령은 URL/trace와 HTTP 오류 처리를 검사합니다. 두 번째는 로컬 HTTP 서버와 실제 Qt 입력/타이머를 사용해 15초 후 반복 실행, 해제/중지, 간격 변경, 중복 측정 방지 및 나눔고딕 적용을 확인합니다. 마지막 명령은 실제 두 도메인을 측정하고 임베디드 지도·타일·연결선이 표시되는지 확인하며 `artifacts/gui-check.png`를 생성합니다.

## 참고

- [Cloudflare cdn-cgi endpoint](https://developers.cloudflare.com/fundamentals/reference/cdn-cgi-endpoint/)
- [Cloudflare colo 설명](https://developers.cloudflare.com/speed/troubleshooting/slow-website/)
- [Leaflet 문서](https://leafletjs.com/reference.html)
- [Material Design 3 색상 역할](https://m3.material.io/styles/color/the-color-system)
- [OpenStreetMap 타일 사용 정책](https://operations.osmfoundation.org/policies/tiles/)
