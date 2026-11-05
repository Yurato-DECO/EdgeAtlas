"""Edge Atlas — desktop Cloudflare ingress viewer."""
import csv
import json
import sys
import os
import threading
import math
from pathlib import Path
# Software rendering avoids blank maps on some Windows GPU / remote sessions.
os.environ.setdefault('QTWEBENGINE_CHROMIUM_FLAGS', '--disable-gpu')
from PySide6.QtCore import Qt, QThread, QTimer, Signal, QSettings, QUrl
from PySide6.QtGui import QColor, QIcon
from PySide6.QtWidgets import QApplication, QMainWindow, QTableWidgetItem, QFileDialog, QMessageBox
from core import bundled_locations, fetch_locations, probe_many, trace_url
from map_server import MapServer
from system_info import SystemInfoWorker, os_description


class ScanWorker(QThread):
    result = Signal(object)
    locations_ready = Signal(dict, str)

    def __init__(self, sites, refresh_locations):
        super().__init__()
        self.sites = sites
        self.refresh_locations = refresh_locations
        self.cancelled = threading.Event()

    def run(self):
        if self.refresh_locations:
            locations, note = fetch_locations()
            self.locations_ready.emit(locations, note)
        if not self.cancelled.is_set():
            for result in probe_many(self.sites, self.cancelled):
                self.result.emit(result)


class MainWindow(QMainWindow):
    def __init__(self, load_system_info=True):
        super().__init__()
        self.setWindowTitle('Edge Atlas · Cloudflare 접속 지도')
        self.setWindowIcon(QIcon(str(Path(__file__).with_name('icon.png'))))
        self.resize(1440, 940)
        self.settings = QSettings('EdgeAtlas', 'EdgeAtlas')
        self.locations = bundled_locations()
        self.results = {}
        self.previous = {}
        self.changes = {}
        self.worker = None
        self.system_worker = None
        self.closing = False
        self.locations_attempted = False
        self.map_ready = False
        self.server = MapServer()
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.setTimerType(Qt.PreciseTimer)
        self.timer.timeout.connect(self.auto_timeout)
        self.countdown_timer = QTimer(self)
        self.countdown_timer.setInterval(250)
        self.countdown_timer.timeout.connect(self.update_auto_status)
        self.map_update_timer = QTimer(self)
        self.map_update_timer.setSingleShot(True)
        self.map_update_timer.setInterval(60)
        self.map_update_timer.timeout.connect(self.flush_map)
        self.build_ui()
        self.restore_settings()
        self.web.loadFinished.connect(self.map_loaded)
        self.web.setUrl(QUrl(self.server.url))
        value, detail = os_description()
        self.os_info.setText(value)
        self.os_info.setToolTip(detail)
        if load_system_info:
            QTimer.singleShot(0, self.refresh_system_info)

    def build_ui(self):
        from material_ui import build_ui
        build_ui(self)

    def restore_settings(self):
        self.sites.setPlainText(self.settings.value('sites', 'www.cloudflare.com\none.one.one.one'))
        self.origin_name.setText(self.settings.value('origin_name', '서울'))
        self.lat.setValue(float(self.settings.value('lat', 37.5665)))
        self.lon.setValue(float(self.settings.value('lon', 126.978)))
        self.interval.setValue(int(self.settings.value('interval', 60)))

    def save_settings(self):
        for key, value in dict(sites=self.sites.toPlainText(), origin_name=self.origin_name.text(),
                               lat=self.lat.value(), lon=self.lon.value(), interval=self.interval.value()).items():
            self.settings.setValue(key, value)

    def map_loaded(self, ok):
        self.map_ready = ok
        if ok:
            self.web.page().runJavaScript('window.configure()')
            self.update_map()
        else:
            self.statusBar().showMessage('지도 문서를 열지 못했습니다. 측정 기능은 사용할 수 있습니다.')

    def start_scan(self):
        if self.worker is not None or self.closing:
            return
        sites = []
        try:
            for line in self.sites.toPlainText().splitlines():
                if not line.strip():
                    continue
                url = trace_url(line)
                if url not in sites:
                    sites.append(url)
            if not sites or len(sites) > 100:
                raise ValueError('측정할 사이트를 1~100개 입력하세요.')
        except ValueError as exc:
            self.auto.setChecked(False)
            QMessageBox.warning(self, '입력 확인', str(exc))
            return
        self.timer.stop()
        self.save_settings()
        for site, result in self.results.items():
            if result.colo:
                self.previous[site] = result.colo
        self.results.clear()
        self.changes.clear()
        self.web.page().runJavaScript('window.selectSite?.("")')
        self.rows = {}
        self.table.setRowCount(len(sites))
        self.details.clear()
        for row, url in enumerate(sites):
            self.rows[url] = row
            self.table.setItem(row, 0, QTableWidgetItem(url.split('/')[2]))
            for col in range(1, 7):
                self.table.setItem(row, col, QTableWidgetItem('대기' if col == 1 else '—'))
        self.start.setEnabled(False)
        self.stop.setEnabled(True)
        self.sites.setEnabled(False)
        self.worker = ScanWorker(sites, not self.locations_attempted)
        self.locations_attempted = True
        self.worker.locations_ready.connect(self.set_locations)
        self.worker.result.connect(self.add_result)
        self.worker.finished.connect(self.scan_finished)
        self.worker.start()
        self.update_auto_status()
        self.update_summary()
        self.update_map()
        self.statusBar().showMessage('측정 중… 현재 PC의 네트워크 / VPN / 시스템 프록시 설정을 사용합니다.')

    def set_locations(self, locations, note):
        self.locations = locations
        self.location_note = note
        self.update_map()

    def add_result(self, result):
        self.results[result.site] = result
        row = self.rows[result.site]
        location = self.locations.get(result.colo, {})
        old = self.previous.get(result.site)
        changed = bool(old and result.colo and old != result.colo)
        self.changes[result.site] = f'{old} → {result.colo}' if changed else ''
        state = '실패' if result.error else self.changes[result.site] or '연결됨'
        values = [state, result.colo or '—', location.get('city', '좌표 미등록' if result.colo else '—'),
                  f'{result.elapsed_ms:,.0f} ms', result.fields.get('tls', '—'), result.timestamp[11:19]]
        for col, value in enumerate(values, 1):
            item = QTableWidgetItem(value)
            item.setToolTip(result.error or ('접속 도시가 변경되었습니다.' if changed else value))
            if col == 1:
                item.setForeground(QColor('#c24132' if result.error else '#b97713' if changed else '#168464'))
            self.table.setItem(row, col, item)
        self.update_summary()
        self.update_map()

    def update_summary(self):
        good = [r for r in self.results.values() if not r.error]
        cities = {r.colo for r in good}
        unknown = sum(r.colo not in self.locations for r in good)
        self.metric_values['completed'].setText(f'{len(self.results)} / {self.table.rowCount()}')
        self.metric_values['connected'].setText(str(len(good)))
        self.metric_values['cities'].setText(str(len(cities)))
        self.metric_values['failed'].setText(str(len(self.results) - len(good)))
        self.summary.setText(f'좌표 미등록 {unknown}개' if unknown else f'{len(self.results)}개 결과')

    def update_map(self, *_):
        if not self.map_update_timer.isActive():
            self.map_update_timer.start()

    def flush_map(self):
        if not self.map_ready:
            return
        # Do not pass the client IP or raw trace fields to the map page.
        payload = dict(origin=dict(name=self.origin_name.text(), lat=self.lat.value(), lon=self.lon.value()),
                       results=[dict(site=r.site.split('/')[2], colo=r.colo, elapsed_ms=r.elapsed_ms,
                                     error=r.error, location=self.locations.get(r.colo)) for r in self.results.values()])
        self.web.page().runJavaScript('window.updateData(' + json.dumps(payload, ensure_ascii=True) + ')')

    def select_result(self):
        row = self.table.currentRow()
        for site, result in self.results.items():
            if self.rows[site] == row:
                text = result.error or '\n'.join(f'{k}={v}' for k, v in result.fields.items())
                self.details.setPlainText(result.url + '\n' + text)
                self.web.page().runJavaScript('window.selectSite(' + json.dumps(site.split('/')[2]) + ')')
                return

    def stop_scan(self):
        self.auto.setChecked(False)
        self.timer.stop()
        self.stop.setEnabled(False)
        if self.worker:
            self.worker.cancelled.set()
            self.stop.setEnabled(False)
            self.statusBar().showMessage('중지 중… 진행 중인 요청이 정리되면 종료합니다.')

    def scan_finished(self):
        cancelled = self.worker.cancelled.is_set()
        self.worker.deleteLater()
        self.worker = None
        for row in range(self.table.rowCount()):
            if self.table.item(row, 1).text() == '대기':
                self.table.item(row, 1).setText('중지됨')
        self.start.setEnabled(True)
        self.stop.setEnabled(False)
        self.sites.setEnabled(True)
        self.map_update_timer.stop()
        self.flush_map()
        self.web.page().runJavaScript('window.fitRoutes?.()')
        self.statusBar().showMessage(('측정 중지' if cancelled else '측정 완료') + ' · ' + getattr(self, 'location_note', '기본 도시 좌표') + ' · 좌표는 도시 수준의 근사치입니다.')
        if self.closing:
            self.close()
        else:
            self.schedule_next_scan()

    def auto_toggled(self, checked):
        self.timer.stop()
        if checked and not self.closing:
            self.countdown_timer.start()
            if self.worker is None:
                self.start_scan()
        else:
            self.countdown_timer.stop()
        self.update_auto_status()

    def interval_changed(self, *_):
        if self.worker is None:
            self.schedule_next_scan()

    def schedule_next_scan(self):
        self.timer.stop()
        if self.auto.isChecked() and not self.closing and self.worker is None:
            self.timer.start(self.interval.value() * 1000)
        self.update_auto_status()

    def auto_timeout(self):
        if self.auto.isChecked() and not self.closing:
            self.start_scan()

    def refresh_system_info(self):
        if self.system_worker is not None or self.closing:
            return
        self.ip_info.setText('조회 중…')
        self.dns_info.setText('조회 중…')
        self.system_refresh.setEnabled(False)
        self.system_worker = SystemInfoWorker(self)
        self.system_worker.info.connect(self.set_system_info)
        self.system_worker.finished.connect(self.system_info_finished)
        self.system_worker.start()

    def set_system_info(self, key, value, detail):
        widget = self.ip_info if key == 'ip' else self.dns_info
        widget.setText(value)
        widget.setMinimumHeight(widget.fontMetrics().lineSpacing() * (value.count('\n') + 1) + 4)
        widget.setToolTip(detail)

    def system_info_finished(self):
        self.system_worker.deleteLater()
        self.system_worker = None
        self.system_refresh.setEnabled(True)
        if self.closing:
            self.close()

    def update_auto_status(self):
        if self.auto.isChecked():
            if self.worker is not None:
                text = '측정 중 · 완료 후 자동으로 다시 측정합니다'
            elif self.timer.isActive():
                seconds = max(0, math.ceil(self.timer.remainingTime() / 1000))
                text = f'다음 측정까지 {seconds}초'
            else:
                text = '자동 측정 준비 중'
        else:
            text = '자동 재측정 꺼짐'
        self.auto_status.setText(text)
        self.stop.setEnabled(self.worker is not None or self.timer.isActive())

    def export_csv(self):
        if not self.results:
            QMessageBox.information(self, 'CSV 저장', '먼저 사이트를 측정하세요.')
            return
        path, _ = QFileDialog.getSaveFileName(self, '결과 저장', 'edge-atlas.csv', 'CSV (*.csv)')
        if not path:
            return
        try:
            with open(path, 'w', newline='', encoding='utf-8-sig') as file:
                writer = csv.writer(file)
                writer.writerow(['site', 'colo', 'city', 'http_ms', 'tls', 'client_country', 'timestamp', 'change', 'error'])
                for r in self.results.values():
                    values = [r.site, r.colo, self.locations.get(r.colo, {}).get('city', ''), r.elapsed_ms,
                              r.fields.get('tls', ''), r.fields.get('loc', ''), r.timestamp, self.changes.get(r.site, ''), r.error]
                    writer.writerow(["'" + str(v) if str(v).startswith(('=', '+', '-', '@', '\t', '\r')) else v for v in values])
            self.statusBar().showMessage(f'CSV 저장 완료: {path}')
        except OSError as exc:
            QMessageBox.warning(self, '저장 실패', str(exc))

    def closeEvent(self, event):
        self.save_settings()
        self.timer.stop()
        self.countdown_timer.stop()
        self.closing = True
        if self.worker is not None:
            self.stop_scan()
            event.ignore()
            return
        if self.system_worker is not None:
            self.statusBar().showMessage('네트워크 정보 조회를 마무리하고 종료합니다…')
            event.ignore()
            return
        self.server.close()
        self.web.page().deleteLater()
        event.accept()


def main():
    if os.name == 'nt':
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('EdgeAtlas.Desktop.1')
    app = QApplication(sys.argv)
    app.setApplicationName('Edge Atlas')
    app.setWindowIcon(QIcon(str(Path(__file__).with_name('icon.png'))))
    window = MainWindow()
    if '--self-test' in sys.argv:
        from packaging_check import configure_check
        index = sys.argv.index('--self-test')
        configure_check(app, window, Path(sys.argv[index + 1]))
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
