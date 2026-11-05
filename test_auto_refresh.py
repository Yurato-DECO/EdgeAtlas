"""Exercise real Qt input, timers and HTTP workers without external traffic."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from PySide6.QtCore import Qt
from PySide6.QtGui import QFontInfo
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from app import MainWindow


class AutoRefreshTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.app.setQuitOnLastWindowClosed(False)

    def setUp(self):
        self.hits = []
        self.delay = 0
        self.status = 200
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                owner.hits.append(time.monotonic())
                time.sleep(owner.delay)
                self.send_response(owner.status)
                self.end_headers()
                self.wfile.write(b'ip=192.0.2.1\ncolo=ICN\n')

            def log_message(self, *args):
                pass

        self.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.window = MainWindow(load_system_info=False)
        self.window.save_settings = lambda: None
        self.window.web.stop()
        self.window.locations_attempted = True
        self.window.sites.setPlainText(f'http://127.0.0.1:{self.server.server_port}')
        self.window.interval.setValue(15)
        self.window.show()

    def wait_until(self, condition, timeout=3000):
        deadline = time.monotonic() + timeout / 1000
        while not condition() and time.monotonic() < deadline:
            QTest.qWait(20)
        self.assertTrue(condition(), 'Expected state did not arrive before timeout')

    def enable_and_wait(self):
        QTest.mouseClick(self.window.auto_label, Qt.LeftButton)
        self.wait_until(lambda: len(self.hits) == 1 and self.window.worker is None)
        self.assertTrue(self.window.timer.isActive())

    def tearDown(self):
        self.window.stop_scan()
        self.wait_until(lambda: self.window.worker is None)
        self.window.close()
        self.window.deleteLater()
        QTest.qWait(30)
        self.app.processEvents()
        self.server.shutdown()
        self.server.server_close()

    def test_real_15_second_repeat_from_label_click(self):
        self.enable_and_wait()
        self.assertIn('다음 측정까지', self.window.auto_status.text())
        self.wait_until(lambda: len(self.hits) >= 2 and self.window.worker is None, 18000)
        self.assertGreaterEqual(self.hits[1] - self.hits[0], 15)
        self.assertTrue(self.window.timer.isActive())

    def test_switch_off_cancels_pending_repeat(self):
        self.window.interval.setMinimum(1)
        self.window.interval.setValue(1)
        self.enable_and_wait()
        QTest.mouseClick(self.window.auto, Qt.LeftButton)
        QTest.qWait(1200)
        self.assertEqual(len(self.hits), 1)
        self.assertFalse(self.window.timer.isActive())
        self.assertEqual(self.window.auto_status.text(), '자동 재측정 꺼짐')

    def test_stop_button_works_between_scans(self):
        self.enable_and_wait()
        self.assertTrue(self.window.stop.isEnabled())
        QTest.mouseClick(self.window.stop, Qt.LeftButton)
        self.assertFalse(self.window.auto.isChecked())
        self.assertFalse(self.window.timer.isActive())
        self.assertFalse(self.window.countdown_timer.isActive())

    def test_interval_edit_reschedules_and_keyboard_can_disable(self):
        self.enable_and_wait()
        self.window.interval.setMinimum(1)
        self.window.interval.setValue(1)
        self.assertLessEqual(self.window.timer.remainingTime(), 1000)
        self.wait_until(lambda: len(self.hits) == 2 and self.window.worker is None)
        self.window.auto.setFocus()
        QTest.keyClick(self.window.auto, Qt.Key_Space)
        self.assertFalse(self.window.auto.isChecked())
        self.assertFalse(self.window.timer.isActive())

    def test_enable_while_running_does_not_start_overlapping_scan(self):
        self.delay = .3
        self.window.start_scan()
        QTest.mouseClick(self.window.auto, Qt.LeftButton)
        self.wait_until(lambda: self.window.worker is None)
        self.assertEqual(len(self.hits), 1)
        self.assertTrue(self.window.timer.isActive())

    def test_http_failure_still_schedules_next_scan(self):
        self.status = 403
        self.enable_and_wait()
        self.assertTrue(next(iter(self.window.results.values())).error)
        self.assertTrue(self.window.auto.isChecked())

    def test_nanum_font_is_actually_resolved(self):
        for widget in (self.window.start, self.window.sites, self.window.table):
            self.assertEqual(QFontInfo(widget.font()).family(), 'NanumGothic')


if __name__ == '__main__':
    unittest.main()
