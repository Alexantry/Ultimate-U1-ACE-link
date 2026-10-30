"""Build an allowlisted public source archive. No device or network access."""
import hashlib
import json
from pathlib import Path
import re
import zipfile
from build_beginner_guide import main as build_beginner_guide

ROOT = Path(__file__).resolve().parents[1]
TOP = {'.gitignore', '.gitattributes', 'README.md', 'README.zh-CN.md', 'LICENSE',
       'THIRD_PARTY.md', 'SOURCES.json', 'manifest.json', 'installer.py', 'CHANGELOG.md',
       'Install.ps1', 'Bootstrap.ps1', 'AceFirmware.ps1', 'START-HERE.cmd', 'START-HERE.html', 'START-HERE.en.html',
       'MANUAL-INSTALL.html'}
TEMPLATES = {'config/settings.example.json', 'config/settings.tested-reference.json'}
TOOL_JSON = {'tools/ace_usb/images.json', 'tools/ace_usb/device-profile.json'}


def source_files():
    result = []
    for path in sorted(ROOT.rglob('*')):
        if not path.is_file() or path.is_symlink():
            continue
        rel = path.relative_to(ROOT).as_posix()
        if any(p in ('.git', '__pycache__', '.venv', 'downloads', 'dist', 'private', 'backups')
               for p in path.relative_to(ROOT).parts):
            continue
        allowed = (rel in TOP or rel in TEMPLATES or rel in TOOL_JSON or
                   (rel.startswith('payload/') and path.name in
                    ('ace.py', 'filament_feed.py', 'filament_detect.py', 'extruder.py')) or
                   (rel.startswith('docs/') and path.suffix in ('.md', '.svg')) or
                   (rel.startswith('tests/') and path.suffix in ('.py', '.ps1')) or
                   (rel.startswith('tools/') and path.suffix == '.py') or
                   rel == '.github/workflows/verify.yml')
        if allowed:
            if path.suffix == '.py':
                compile(path.read_bytes(), rel, 'exec')
            result.append((rel, path))
    assert result and all((ROOT / x).is_file() for x in TOP), 'Missing required source file'
    return result


def main():
    build_beginner_guide()
    manifest = json.loads((ROOT / 'manifest.json').read_text(encoding='utf8'))
    version = manifest['release']
    assert re.fullmatch(r'\d+\.\d+\.\d+', version)
    for item in manifest['files']:
        data = (ROOT / item['payload']).read_bytes()
        assert hashlib.sha256(data).hexdigest() == item['sha256'], item['payload']
    profile = json.loads((ROOT / 'tools/ace_usb/device-profile.json').read_text())
    assert profile['write_enabled'] is False
    assert all(value is False for value in profile['checks'].values())
    files = source_files()
    checksums = ''.join(hashlib.sha256(p.read_bytes()).hexdigest() + '  ' + rel + '\n'
                        for rel, p in files)
    prefix = 'Ultimate-U1-ACE-link/'
    out = ROOT / 'downloads'
    out.mkdir(exist_ok=True)
    archive = out / ('Ultimate-U1-ACE-link-v' + version + '.zip')
    with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for rel, p in files:
            info = zipfile.ZipInfo(prefix + rel, (2026, 10, 30, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            z.writestr(info, p.read_bytes())
        info = zipfile.ZipInfo(prefix + 'PACKAGE-SHA256SUMS', (2026, 10, 30, 0, 0, 0))
        info.compress_type = zipfile.ZIP_DEFLATED
        info.external_attr = 0o100644 << 16
        z.writestr(info, checksums)
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        assert len(z.namelist()) == len(files) + 1
        for rel, p in files:
            assert z.read(prefix + rel) == p.read_bytes(), rel
        assert not any(n.endswith(('.bin', '.pyc', '.key', '.pem', 'openrfid_user.cfg')) for n in z.namelist())
    archive_hash = hashlib.sha256(archive.read_bytes()).hexdigest()
    sums = archive_hash + '  ' + archive.name + '\n'
    retained_sums = ''
    for previous, previous_hash in [
            ('0.1.0', '81c21610c49b6e5861e1676cc2662df77bff447c6d24848881a6719319b13c1e'),
            ('0.1.1', 'f684badeac36d7a66d47ed65c04ae0ec278e5731a5289aabaa8a7c521e86b497'),
            ('0.1.2', '2663853d3bab97efa09b579b110af099e852ffd7aee06d3afe105ea73e8a5c1c'),
            ('0.1.3', '03de055d1c38d430f83817d5687c73dc387a3f282a2c4329df0b8ce882349e39'),
            ('0.1.4', '9ab8c4ff1b0ef2f6319f7478a684ffec381ab21c2a666f0e7f3ea27e22b8a6e1')]:
        retained = out / ('Ultimate-U1-ACE-link-v' + previous + '.zip')
        if retained.exists():
            assert hashlib.sha256(retained.read_bytes()).hexdigest() == previous_hash, 'Retained v' + previous + ' changed'
            retained_sums += previous_hash + '  ' + retained.name + '\n'
    sums = retained_sums + sums
    (out / 'SHA256SUMS').write_text(sums, encoding='ascii')
    print(json.dumps({'archive': archive.name, 'files': len(files),
                      'bytes': archive.stat().st_size, 'sha256': archive_hash,
                      'private_configuration_included': False}, indent=2))


if __name__ == '__main__':
    main()

