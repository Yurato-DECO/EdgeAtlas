"""Material 3 inspired Qt Widgets presentation layer for Edge Atlas."""
from pathlib import Path
from PySide6.QtCore import Qt, QSize, QRectF, Property, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QColor, QPainter, QIcon, QPixmap, QPen, QFont, QFontDatabase
from PySide6.QtWidgets import (
    QApplication, QWidget, QFrame, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QFormLayout, QPlainTextEdit, QLineEdit, QSpinBox, QDoubleSpinBox, QCheckBox,
    QScrollArea, QSplitter, QTableWidget, QHeaderView, QAbstractItemView,
    QStyledItemDelegate, QStyle,
)
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEngineProfile, QWebEnginePage

# Material semantic roles. Keep colors centralized for the desktop surface.
COLORS = dict(primary='#4355b9', on_primary='#ffffff', primary_container='#dfe3ff',
              on_primary_container='#18266c', surface='#f9f9ff', container_low='#f1f3fb',
              container='#ebedf7', highest='#e1e4ee', on_surface='#1a1b25',
              on_surface_variant='#454754', outline='#757785', outline_variant='#c5c6d4',
              error='#ba1a1a', error_container='#ffdad6', secondary_container='#e1e4f4')


def icon(name, color='#4355b9'):
    paths = {
        'play': '<path d="m8 5 11 7-11 7z" fill="currentColor" stroke="none"/>',
        'stop': '<rect x="6" y="6" width="12" height="12" rx="2" fill="currentColor" stroke="none"/>',
        'map': '<path d="m3 5 6-2 6 2 6-2v16l-6 2-6-2-6 2zM9 3v16M15 5v16"/>',
        'download': '<path d="M12 3v12m-5-5 5 5 5-5M4 16v5h16v-5"/>',
        'fit': '<path d="M8 3H3v5m13-5h5v5M3 16v5h5m13-5v5h-5"/><circle cx="12" cy="12" r="3"/>',
        'pin': '<path d="M19 10c0 5-7 11-7 11S5 15 5 10a7 7 0 1 1 14 0z"/><circle cx="12" cy="10" r="2.5"/>',
        'network': '<circle cx="5" cy="7" r="3"/><circle cx="19" cy="5" r="3"/><circle cx="16" cy="19" r="3"/><path d="m8 7 8-2M7 10l7 7m4-9-1 8"/>',
        'refresh': '<path d="M20 7v5h-5M4 17v-5h5M6 6a8 8 0 0 1 13 2M18 18a8 8 0 0 1-13-2"/>',
    }
    svg = ('<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" '
           f'fill="none" stroke="{color}" color="{color}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">'
           + paths[name].replace('currentColor', color) + '</svg>')
    pixmap = QPixmap()
    pixmap.loadFromData(svg.encode(), 'SVG')
    return QIcon(pixmap)


class MaterialSwitch(QCheckBox):
    """Keyboard-accessible checkbox semantics with a Material switch appearance."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAccessibleName('자동으로 다시 측정')
        self.setToolTip('측정 완료 후 설정한 간격으로 다시 측정합니다.')
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(56, 36)
        self._position = 0.0
        self.animation = QPropertyAnimation(self, b'position', self)
        self.animation.setDuration(160)
        self.animation.setEasingCurve(QEasingCurve.OutCubic)
        self.toggled.connect(self.animate)

    def animate(self, checked):
        self.animation.stop()
        self.animation.setStartValue(self._position)
        self.animation.setEndValue(1.0 if checked else 0.0)
        self.animation.start()

    def get_position(self):
        return self._position

    def set_position(self, value):
        self._position = value
        self.update()

    position = Property(float, get_position, set_position)

    def hitButton(self, pos):
        return self.rect().contains(pos)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        if not self.isEnabled():
            p.setOpacity(.38)
        checked = self.isChecked()
        p.setPen(QPen(QColor(COLORS['primary'] if checked else COLORS['outline']), 2))
        p.setBrush(QColor(COLORS['primary'] if checked else COLORS['highest']))
        p.drawRoundedRect(QRectF(3, 4, 50, 28), 14, 14)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor('#ffffff' if checked else COLORS['outline']))
        radius = 8 + 3 * self._position
        x = 17 + 22 * self._position
        p.drawEllipse(QRectF(x-radius, 18-radius, radius*2, radius*2))
        if checked:
            p.setPen(QPen(QColor(COLORS['primary']), 1.8))
            p.drawLine(int(x-4), 18, int(x-1), 21)
            p.drawLine(int(x-1), 21, int(x+5), 15)
        if self.hasFocus():
            p.setBrush(Qt.NoBrush)
            p.setPen(QPen(QColor(COLORS['primary']), 1, Qt.DotLine))
            p.drawRoundedRect(QRectF(0.5, .5, 55, 35), 17, 17)


class ChipDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        painter.save()
        if option.state & QStyle.State_Selected:
            painter.fillRect(option.rect, QColor('#e8ebff'))
        text = index.data() or '—'
        bg, fg = '#ebedf7', '#454754'
        if index.column() == 2 and text != '—':
            bg, fg = '#dfe3ff', '#18266c'
        elif text == '연결됨':
            bg, fg = '#ddf4e6', '#17643b'
        elif text == '실패':
            bg, fg = '#ffdad6', '#93000a'
        elif '→' in text:
            bg, fg = '#ffedce', '#754b00'
        rect = QRectF(option.rect.x()+10, option.rect.center().y()-13,
                      min(option.fontMetrics.horizontalAdvance(text)+22, option.rect.width()-16), 26)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(bg))
        painter.drawRoundedRect(rect, 8, 8)
        painter.setPen(QColor(fg))
        painter.drawText(rect, Qt.AlignCenter, text)
        if option.state & QStyle.State_HasFocus:
            painter.setBrush(Qt.NoBrush)
            painter.setPen(QPen(QColor(COLORS['primary']), 1))
            painter.drawRoundedRect(rect, 8, 8)
        painter.restore()


def label(text, role='body'):
    item = QLabel(text)
    item.setObjectName(role)
    return item


def button(text, symbol, role='tonal'):
    item = QPushButton(text)
    item.setObjectName(role)
    item.setIcon(icon(symbol, '#ffffff' if role == 'primary' else COLORS['primary']))
    item.setIconSize(QSize(18, 18))
    item.setCursor(Qt.PointingHandCursor)
    item.setMinimumHeight(40)
    return item


def card(role='card'):
    widget = QFrame()
    widget.setObjectName(role)
    layout = QVBoxLayout(widget)
    layout.setContentsMargins(20, 18, 20, 18)
    layout.setSpacing(12)
    return widget, layout


def build_ui(w):
    application = QApplication.instance()
    application.setStyle('Fusion')
    if not application.property('nanumFontsLoaded'):
        for weight in ('Regular', 'Bold'):
            path = Path(__file__).parent / 'assets' / 'fonts' / 'nanum-gothic' / f'NanumGothic-{weight}.ttf'
            if QFontDatabase.addApplicationFont(str(path)) < 0:
                raise RuntimeError(f'나눔고딕 폰트를 불러오지 못했습니다: {path}')
        application.setProperty('nanumFontsLoaded', True)
    application.setFont(QFont('NanumGothic', 10))
    root = QWidget()
    w.setCentralWidget(root)
    outer = QVBoxLayout(root)
    outer.setContentsMargins(24, 16, 24, 8)
    outer.setSpacing(16)
    top = QHBoxLayout()
    logo = QLabel()
    logo.setObjectName('logo')
    logo.setPixmap(icon('network').pixmap(24, 24))
    logo.setAlignment(Qt.AlignCenter)
    logo.setFixedSize(48, 48)
    top.addWidget(logo)
    top.addSpacing(4)
    top.addWidget(label('Edge Atlas', 'appTitle'))
    top.addStretch()
    top.addWidget(label('●  OpenStreetMap', 'providerChip'))
    outer.addLayout(top)

    heading = QHBoxLayout()
    titles = QVBoxLayout()
    titles.setSpacing(4)
    titles.addWidget(label('네트워크 연결 지도', 'headline'))
    titles.addWidget(label('내 연결이 도착한 Cloudflare 도시를 확인하세요.', 'supporting'))
    heading.addLayout(titles)
    heading.addStretch()
    outer.addLayout(heading)
    split = QSplitter(Qt.Horizontal)
    split.setChildrenCollapsible(False)
    split.setHandleWidth(16)
    outer.addWidget(split, 1)

    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QFrame.NoFrame)
    scroll.setMinimumWidth(300)
    scroll.setMaximumWidth(380)
    sidebar = QWidget()
    side = QVBoxLayout(sidebar)
    side.setContentsMargins(0, 0, 0, 0)
    side.setSpacing(16)
    scroll.setWidget(sidebar)
    scan_card, scan = card()
    scan.addWidget(label('측정 설정', 'sectionTitle'))
    scan.addWidget(label('사이트', 'fieldLabel'))
    w.sites = QPlainTextEdit()
    w.sites.setAccessibleName('측정할 사이트 목록')
    w.sites.setPlaceholderText('도메인 또는 URL을 한 줄에 하나씩\nwww.cloudflare.com')
    w.sites.setMinimumHeight(112)
    w.sites.setMaximumHeight(144)
    scan.addWidget(w.sites, 1)
    scan.addWidget(label('최대 100개 · 한 줄에 사이트 하나', 'supporting'))
    actions = QHBoxLayout()
    w.start = button('측정 시작', 'play', 'primary')
    w.start.clicked.connect(w.start_scan)
    w.stop = button('중지', 'stop', 'outlined')
    w.stop.setEnabled(False)
    w.stop.clicked.connect(w.stop_scan)
    actions.addWidget(w.start, 2)
    actions.addWidget(w.stop, 1)
    scan.addLayout(actions)
    auto_row = QHBoxLayout()
    w.auto_label = QPushButton('자동 재측정')
    w.auto_label.setObjectName('switchLabel')
    w.auto_label.setCursor(Qt.PointingHandCursor)
    w.auto_label.setToolTip('켜면 지금 측정하고, 완료 후 설정한 간격으로 반복합니다.')
    auto_row.addWidget(w.auto_label)
    auto_row.addStretch()
    w.auto = MaterialSwitch()
    w.auto.toggled.connect(w.auto_toggled)
    w.auto_label.clicked.connect(w.auto.toggle)
    auto_row.addWidget(w.auto)
    scan.addLayout(auto_row)
    interval_row = QHBoxLayout()
    interval_row.addWidget(label('측정 간격', 'supporting'))
    interval_row.addStretch()
    w.interval = QSpinBox()
    w.interval.setAccessibleName('자동 재측정 간격')
    w.interval.setRange(15, 3600)
    w.interval.setValue(60)
    w.interval.setSuffix(' 초')
    w.interval.setFixedWidth(110)
    w.interval.valueChanged.connect(w.interval_changed)
    interval_row.addWidget(w.interval)
    scan.addLayout(interval_row)
    w.auto_status = label('자동 재측정 꺼짐', 'supporting')
    w.auto_status.setWordWrap(True)
    scan.addWidget(w.auto_status)
    side.addWidget(scan_card)

    origin_card, origin = card()
    origin.addWidget(label('지도 출발점', 'sectionTitle'))
    w.origin_name = QLineEdit('서울')
    w.lat, w.lon = QDoubleSpinBox(), QDoubleSpinBox()
    w.lat.setRange(-85, 85)
    w.lon.setRange(-180, 180)
    w.lat.setDecimals(5)
    w.lon.setDecimals(5)
    w.lat.setValue(37.5665)
    w.lon.setValue(126.978)
    form = QFormLayout()
    form.setSpacing(12)
    for text, field in [('이름', w.origin_name), ('위도', w.lat), ('경도', w.lon)]:
        field.setAccessibleName('출발점 ' + text)
        form.addRow(label(text, 'fieldLabel'), field)
    origin.addLayout(form)
    w.origin_name.textChanged.connect(w.update_map)
    w.lat.valueChanged.connect(w.update_map)
    w.lon.valueChanged.connect(w.update_map)
    hint = label('출발점은 직접 지정한 위치입니다.\n도시 좌표는 대략적인 위치를 나타냅니다.', 'supporting')
    hint.setWordWrap(True)
    origin.addWidget(hint)
    side.addWidget(origin_card)
    side.addStretch()
    device = QWidget()
    device_layout = QVBoxLayout(device)
    device_layout.setContentsMargins(14, 4, 14, 4)
    device_layout.setSpacing(7)
    device_header = QHBoxLayout()
    device_header.addWidget(label('내 네트워크', 'fieldLabel'))
    device_header.addStretch()
    w.system_refresh = button('', 'refresh', 'textButton')
    w.system_refresh.setFixedSize(32, 32)
    w.system_refresh.setMinimumHeight(32)
    w.system_refresh.setStyleSheet('padding: 0; border-radius: 16px;')
    w.system_refresh.setAccessibleName('공인 IP 및 DNS 정보 새로고침')
    w.system_refresh.setToolTip('네트워크 정보 새로고침')
    w.system_refresh.clicked.connect(w.refresh_system_info)
    device_header.addWidget(w.system_refresh)
    device_layout.addLayout(device_header)
    info_form = QFormLayout()
    info_form.setSpacing(8)
    w.ip_info, w.dns_info, w.os_info = label('조회 중…', 'deviceValue'), label('조회 중…', 'deviceValue'), label('조회 중…', 'deviceValue')
    for caption, field in [('공인 IP', w.ip_info), ('DNS (OS 설정)', w.dns_info), ('OS', w.os_info)]:
        field.setWordWrap(True)
        field.setTextInteractionFlags(Qt.TextSelectableByMouse)
        field.setAccessibleName(caption)
        info_form.addRow(label(caption, 'supporting'), field)
    device_layout.addLayout(info_form)
    # Keep device information visible at the lower left while settings scroll.
    sidebar_shell = QWidget()
    sidebar_shell.setMinimumWidth(300)
    sidebar_shell.setMaximumWidth(380)
    sidebar_layout = QVBoxLayout(sidebar_shell)
    sidebar_layout.setContentsMargins(0, 0, 0, 0)
    sidebar_layout.setSpacing(8)
    sidebar_layout.addWidget(scroll, 1)
    sidebar_layout.addWidget(device)
    split.addWidget(sidebar_shell)

    content = QWidget()
    main = QVBoxLayout(content)
    main.setContentsMargins(0, 0, 0, 0)
    main.setSpacing(12)
    metrics = QHBoxLayout()
    metrics.setSpacing(12)
    w.metric_values = {}
    for key, text, value in [('completed', '측정 완료', '0 / 0'), ('connected', '연결 성공', '0'),
                             ('cities', '접속 지점', '0'), ('failed', '연결 실패', '0')]:
        metric, layout = card('metricPrimary' if key == 'completed' else 'metric')
        layout.setContentsMargins(18, 12, 18, 12)
        layout.setSpacing(4)
        layout.addWidget(label(text, 'metricLabel'))
        number = label(value, 'metricValue')
        layout.addWidget(number)
        w.metric_values[key] = number
        metrics.addWidget(metric, 1)
    main.addLayout(metrics)

    map_card, map_layout = card('mapCard')
    map_layout.setContentsMargins(12, 10, 12, 10)
    map_layout.setSpacing(8)
    map_header = QHBoxLayout()
    map_header.setContentsMargins(8, 0, 0, 0)
    map_header.addWidget(label('접속 지도', 'sectionTitle'))
    map_header.addStretch()
    fit = button('전체 보기', 'fit', 'textButton')
    fit.clicked.connect(lambda: w.web.page().runJavaScript('window.fitRoutes?.()'))
    map_header.addWidget(fit)
    map_layout.addLayout(map_header)
    w.web = QWebEngineView()
    w.map_profile = QWebEngineProfile('EdgeAtlasMaps', w)
    w.map_profile.setHttpUserAgent('EdgeAtlas/1.0 (QtWebEngine; desktop map viewer)')
    w.map_profile.setHttpCacheType(QWebEngineProfile.DiskHttpCache)
    w.web.setPage(QWebEnginePage(w.map_profile, w.web))
    w.web.setMinimumHeight(220)
    map_layout.addWidget(w.web, 1)
    note = label('출발점과 접속 도시를 연결한 개념도 · 실제 중간 라우터 경로는 표시하지 않습니다.', 'supporting')
    note.setWordWrap(True)
    note.setContentsMargins(8, 0, 8, 0)
    map_layout.addWidget(note)
    main.addWidget(map_card, 5)

    results_card, results = card('resultsCard')
    results.setContentsMargins(12, 10, 12, 12)
    results.setSpacing(8)
    result_header = QHBoxLayout()
    result_header.setContentsMargins(8, 0, 0, 0)
    result_header.addWidget(label('측정 결과', 'sectionTitle'))
    w.summary = label('측정 대기', 'supporting')
    result_header.addWidget(w.summary)
    result_header.addStretch()
    w.export = button('CSV 저장', 'download', 'tonal')
    w.export.clicked.connect(w.export_csv)
    result_header.addWidget(w.export)
    results.addLayout(result_header)
    w.table = QTableWidget(0, 7)
    w.table.setAccessibleName('사이트별 접속 지점 측정 결과')
    w.table.setHorizontalHeaderLabels(['사이트', '상태 / 변경', 'COLO', '도시', 'HTTP 소요', 'TLS', '시각'])
    w.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
    w.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
    w.table.horizontalHeader().setMinimumSectionSize(72)
    w.table.verticalHeader().setDefaultSectionSize(44)
    w.table.setSelectionBehavior(QAbstractItemView.SelectRows)
    w.table.setSelectionMode(QAbstractItemView.SingleSelection)
    w.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
    w.table.verticalHeader().hide()
    w.table.setShowGrid(False)
    w.table.setItemDelegateForColumn(1, ChipDelegate(w.table))
    w.table.setItemDelegateForColumn(2, ChipDelegate(w.table))
    w.table.itemSelectionChanged.connect(w.select_result)
    w.table.setMinimumHeight(135)
    results.addWidget(w.table, 1)
    w.details = QPlainTextEdit()
    w.details.setObjectName('traceDetails')
    w.details.setReadOnly(True)
    w.details.setAccessibleName('선택한 사이트의 trace 상세 정보')
    w.details.setPlaceholderText('결과를 선택하면 trace 상세 정보가 여기에 표시됩니다.')
    w.details.setFixedHeight(64)
    results.addWidget(w.details)
    main.addWidget(results_card, 3)
    split.addWidget(content)
    split.setSizes([320, 1060])
    w.statusBar().setSizeGripEnabled(False)
    w.statusBar().showMessage('준비됨 · 사이트를 입력하고 측정을 시작하세요.')
    w.setStyleSheet(STYLESHEET.replace('@ASSETS@', (Path(__file__).parent / 'assets' / 'ui').as_posix()))


STYLESHEET = '''
QMainWindow, QWidget { background: #f9f9ff; color: #1a1b25; font-family: "NanumGothic"; font-size: 13px; }
QLabel { background: transparent; border: none; }
QLabel#appTitle {font-size: 22px; font-weight: 600;}
QLabel#headline {font-size: 28px; font-weight: 600;}
QLabel#logo {background: #dfe3ff; border-radius: 16px;}
QLabel#providerChip {background: #e1e4f4; color: #454d68; border-radius: 16px; padding: 8px 16px; font-size: 12px; font-weight: 600;}
QLabel#supporting {color: #454754; font-size: 12px;}
QLabel#fieldLabel {color: #454754; font-size: 12px; font-weight: 600;}
QLabel#deviceValue {color: #1a1b25; font-size: 12px;}
QLabel#sectionTitle {font-size: 16px; font-weight: 600;}
QFrame#card {background: #f1f3fb; border-radius: 20px;}
QFrame#metric {background: #ebedf7; border-radius: 20px;}
QFrame#metricPrimary {background: #dfe3ff; border-radius: 20px;}
QLabel#metricLabel {font-size: 12px; color: #454754;}
QLabel#metricValue {font-size: 27px; color: #18266c; font-weight: 600;}
QFrame#mapCard, QFrame#resultsCard {background: #ffffff; border: 1px solid #e1e4ee; border-radius: 20px;}
QPlainTextEdit, QLineEdit, QSpinBox, QDoubleSpinBox {background: #ffffff; border: 1px solid #757785; border-radius: 6px; padding: 9px 12px; selection-background-color: #dfe3ff; selection-color: #18266c;}
QPlainTextEdit:focus, QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {border: 2px solid #4355b9; padding: 8px 11px;}
QPlainTextEdit:disabled {background: #ebedf7; color: #757785; border-color: #c5c6d4;}
QPlainTextEdit#traceDetails {background: #f1f3fb; border: 0; border-radius: 10px; font-size: 12px; padding: 10px;}
QSpinBox, QDoubleSpinBox {min-height: 20px; padding-right: 24px;}
QSpinBox::up-button, QDoubleSpinBox::up-button {subcontrol-origin: border; subcontrol-position: top right; width: 22px; border: none; border-top-right-radius: 6px; margin: 1px;}
QSpinBox::down-button, QDoubleSpinBox::down-button {subcontrol-origin: border; subcontrol-position: bottom right; width: 22px; border: none; border-bottom-right-radius: 6px; margin: 1px;}
QSpinBox::up-button:hover, QSpinBox::down-button:hover, QDoubleSpinBox::up-button:hover, QDoubleSpinBox::down-button:hover {background: #dfe3ff;}
QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {image: url("@ASSETS@/chevron-up.svg"); width: 12px; height: 12px;}
QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {image: url("@ASSETS@/chevron-down.svg"); width: 12px; height: 12px;}
QPushButton {background: #e1e4f4; color: #18266c; border: 1px solid transparent; border-radius: 20px; padding: 0 18px; font-size: 13px; font-weight: 600;}
QPushButton:hover {background: #d5d9ee;}
QPushButton:pressed {background: #c6cce7;}
QPushButton:focus {border: 2px solid #4355b9; padding: 0 17px;}
QPushButton#primary {background: #4355b9; color: #ffffff;}
QPushButton#primary:hover {background: #5263c3;}
QPushButton#primary:pressed {background: #35459e;}
QPushButton#primary:focus {border-color: #18266c;}
QPushButton#outlined {background: transparent; border: 1px solid #757785; color: #4355b9;}
QPushButton#outlined:hover, QPushButton#textButton:hover {background: #edf0ff;}
QPushButton#outlined:pressed, QPushButton#textButton:pressed {background: #dfe3ff;}
QPushButton#textButton {background: transparent; color: #4355b9;}
QPushButton#switchLabel {background: transparent; color: #1a1b25; border: 0; padding: 8px 0; text-align: left; font-weight: 400;}
QPushButton#switchLabel:hover {color: #4355b9;}
QPushButton#switchLabel:focus {border-bottom: 1px solid #4355b9; border-radius: 0;}
QPushButton:disabled, QPushButton#primary:disabled, QPushButton#outlined:disabled {background: #e5e6ee; color: #777984; border-color: transparent;}
QTableWidget {background: #ffffff; border: none; selection-background-color: #e8ebff; selection-color: #18266c; outline: none;}
QTableWidget::item {padding: 8px 10px; border-bottom: 1px solid #eef0f7;}
QTableWidget::item:hover {background: #f1f3fb;}
QHeaderView::section {background: #f1f3fb; color: #454754; border: none; padding: 10px; font-size: 12px; font-weight: 600;}
QScrollArea, QScrollArea > QWidget > QWidget {background: transparent; border: none;}
QScrollBar:vertical {background: transparent; width: 8px; margin: 2px;}
QScrollBar::handle:vertical {background: #c5c6d4; border-radius: 3px; min-height: 28px;}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {height: 0;}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {background: transparent;}
QScrollBar:horizontal {background: transparent; height: 8px; margin: 2px;}
QScrollBar::handle:horizontal {background: #c5c6d4; border-radius: 3px; min-width: 28px;}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {width: 0;}
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {background: transparent;}
QSplitter::handle {background: transparent;}
QStatusBar {background: #f9f9ff; color: #454754; font-size: 11px; padding: 4px 18px;}
QToolTip {background: #30313b; color: #ffffff; padding: 8px; border: none;}
'''
