"""Explicit --self-test mode for verifying the distributed executable."""
import json
from pathlib import Path
from PySide6.QtCore import QTimer
from PySide6.QtGui import QFontInfo


def configure_check(app, window, report_path):
    report_path = Path(report_path).resolve()
    report_path.parent.mkdir(parents=True, exist_ok=True)
    window.save_settings = lambda: None
    window.sites.setPlainText('www.cloudflare.com\none.one.one.one')
    window.setEnabled(False)
    outcome = {'done': False}
    # Keep the callbacks alive until the event loop has finished.
    window._package_check = outcome

    def finish(value=None):
        if outcome['done']:
            return
        outcome['done'] = True
        state = json.loads(value) if value else {'error': 'Package check timed out'}
        state['font'] = QFontInfo(window.sites.font()).family()
        state['window_icon'] = not window.windowIcon().isNull()
        state['system_info'] = {
            'public_ip_loaded': window.ip_info.text() not in ('조회 중…', '조회 실패'),
            'dns_loaded': window.dns_info.text() not in ('조회 중…', '조회 실패', '설정 정보 없음'),
            'os_loaded': 'Windows' in window.os_info.text(),
        }
        state['trace_results'] = [{'colo': r.colo, 'ok': not bool(r.error)} for r in window.results.values()]
        state['ok'] = bool(state.get('map') and state.get('tiles', 0) > 0 and state.get('fonts')
                           and state.get('layers', 0) > 2 and state['window_icon']
                           and state['font'] == 'NanumGothic'
                           and all(state['system_info'].values())
                           and len(state['trace_results']) == 2 and all(r['ok'] for r in state['trace_results']))
        report_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding='utf-8')
        window.setEnabled(True)
        app.processEvents()
        window.grab().save(str(report_path.with_suffix('.png')))
        if window.worker is not None:
            window.worker.cancelled.set()
            window.worker.finished.connect(lambda: app.exit(1))
        else:
            QTimer.singleShot(0, lambda: app.exit(0 if state['ok'] else 1))
        window.close()

    def inspect():
        if outcome['done']:
            return
        if window.worker is not None or window.system_worker is not None or len(window.results) < 2 or not window.map_ready:
            QTimer.singleShot(300, inspect)
            return
        js = """JSON.stringify({map:!!map,layers:layers.length,
            fonts:document.fonts.check('13px NanumGothic'),timing:window.mapTiming,
            tiles:[...document.querySelectorAll('.leaflet-tile')].filter(i=>i.complete&&i.naturalWidth>0).length,
            mapError:document.getElementById('error').textContent})"""
        window.web.page().runJavaScript(js, finish)

    QTimer.singleShot(500, window.start_scan)
    QTimer.singleShot(10000, inspect)
    QTimer.singleShot(45000, finish)
