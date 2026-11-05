"""Assemble the portable directory and ZIP after a successful PyInstaller build."""
from importlib.metadata import distribution
from pathlib import Path
import shutil
import sys
import zipfile

root = Path(__file__).resolve().parent
release = root / 'dist' / 'EdgeAtlas'
if not (release / 'EdgeAtlas.exe').is_file():
    raise SystemExit('Build EdgeAtlas.spec first.')
shutil.copy2(root / 'README.md', release / 'README.md')
(release / '실행방법.txt').write_text(
    'Edge Atlas\n\n'
    '1. ZIP 파일을 폴더에 전체 압축 해제합니다.\n'
    '2. EdgeAtlas.exe를 더블클릭합니다. Python 설치는 필요 없습니다.\n'
    '3. _internal 폴더는 EXE와 함께 유지하세요.\n\n'
    '지도와 사이트 측정에는 인터넷 연결이 필요합니다.\n'
    '자동 재측정을 켜면 즉시 측정하고 설정한 간격으로 반복합니다.\n'
    '자세한 사용법은 README.md를 참고하세요.\n', encoding='utf-8-sig')
licenses = release / 'licenses'
licenses.mkdir(exist_ok=True)
for name in ('PySide6', 'PySide6_Essentials', 'PySide6_Addons', 'PySide6_WebEngine',
             'shiboken6', 'requests', 'urllib3', 'certifi', 'charset-normalizer', 'idna'):
    package = distribution(name)
    for file in package.files or []:
        if '.dist-info/' in str(file) and any(token in str(file).lower() for token in ('license', 'notice', 'copying')):
            dest = licenses / name / Path(str(file)).name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(package.locate_file(file), dest)
shutil.copy2(Path(sys.base_prefix) / 'LICENSE.txt', licenses / 'Python.txt')
archive = root / 'dist' / 'EdgeAtlas-Windows-x64.zip'
with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as bundle:
    for path in sorted(release.rglob('*')):
        if path.is_file():
            bundle.write(path, path.relative_to(release.parent))
print(f'Ready: {archive} ({archive.stat().st_size / 1024**2:.1f} MiB)')
