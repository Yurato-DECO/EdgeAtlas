"""Integration check: embedded JS, OSM map, arc rendering, real trace, screenshot."""
import json
import os
from pathlib import Path
from PySide6.QtCore import QTimer
from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import QApplication
from app import MainWindow

app = QApplication([])
if os.environ.get('QT_QPA_PLATFORM') == 'offscreen':
    for name in ['segoeui.ttf', 'segoeuib.ttf', 'malgun.ttf', 'malgunbd.ttf']:
        QFontDatabase.addApplicationFont('C:/Windows/Fonts/' + name)
window = MainWindow()
window.save_settings = lambda: None
window.show()
window.setEnabled(False)
window.sites.setPlainText('www.cloudflare.com\none.one.one.one')
checks = {'finished': False}


def inspect():
    if window.worker is not None:
        QTimer.singleShot(500, inspect)
        return
    js = """JSON.stringify({leaflet:!!window.L,map:!!map,layers:layers.length,
        error:document.getElementById('error').textContent,timing:window.mapTiming,
        nanumLoaded:document.fonts.check('13px NanumGothic'),
        mapFont:getComputedStyle(document.getElementById('map')).fontFamily,
        externalLibraries:performance.getEntriesByType('resource').filter(r=>r.name.includes('unpkg.com')).length,
        continuous:arc([37.5665,126.978],[34.05,-118.24]).every((p,i,a)=>!i||Math.abs(p[1]-a[i-1][1])<180),
        tiles:[...document.querySelectorAll('.leaflet-tile')].filter(i=>i.complete&&i.naturalWidth>0).length})"""
    window.web.page().runJavaScript(js, finish)


def finish(value):
    state = json.loads(value or '{}')
    state['results'] = [{'colo': r.colo, 'ok': not bool(r.error)} for r in window.results.values()]
    print(json.dumps(state), flush=True)
    checks['finished'] = True
    checks['ok'] = bool(state.get('map') and state.get('continuous') and state.get('tiles') and state.get('nanumLoaded') and
                        state.get('layers', 0) > 1 and any(r['ok'] for r in state['results']))
    Path('artifacts').mkdir(exist_ok=True)
    QTimer.singleShot(1500, capture)


def capture():
    window.setEnabled(True)
    app.processEvents()
    window.grab().save('artifacts/gui-check.png')
    window.close()


QTimer.singleShot(1000, window.start_scan)
QTimer.singleShot(10000, inspect)
QTimer.singleShot(45000, window.close)
app.exec()
raise SystemExit(0 if checks.get('ok') else 1)
