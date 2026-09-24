"""The student release zip: right contents, nothing that shouldn't ship."""

import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_release_zip_contents(tmp_path):
    r = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "make_release_zip.py"),
         "--out", str(tmp_path)],
        capture_output=True, text=True, cwd=str(ROOT))
    assert r.returncode == 0, r.stderr
    out = tmp_path / "DigitalLabCoach.zip"
    assert out.exists()
    z = zipfile.ZipFile(out)
    names = z.namelist()

    assert all(n.startswith("DigitalLabCoach-") for n in names)
    for frag in ("dlc/web/server.py", "proxy/dlc_proxy.py",
                 "prompts/", "data/sample_circuits/",
                 "data/official_tests_defaults.json",
                 "START_HERE.bat", "start.sh", "UNINSTALL.bat",
                 "uninstall.sh", "README.md", "uv.lock",
                 "docs/RELEASE_GUIDE.md"):
        assert any(frag in n for n in names), f"missing {frag}"

    for bad in ("/tests/", "__pycache__", ".venv", ".git/",
                ".pytest_cache", ".pyc"):
        assert not any(bad in n for n in names), f"shipped {bad}"

    for launcher in ("/start.sh", "/uninstall.sh"):
        sh = next(i for i in z.infolist() if i.filename.endswith(launcher))
        assert (sh.external_attr >> 16) & 0o111, f"{launcher} lost its exec bit"
        assert sh.create_system == 3, \
            f"{launcher} is stamped as made on Windows: macOS would drop its exec bit"
    for n in names:
        if n.endswith(".sh"):
            assert b"\r" not in z.read(n), f"{n} would fail on macOS (CRLF)"
        if n.endswith(".bat"):
            assert b"\r\n" in z.read(n), f"{n} lost its CRLF endings"


def test_release_zip_fixes_line_endings_from_a_windows_checkout(tmp_path):
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "make_release_zip", ROOT / "scripts" / "make_release_zip.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    sh = tmp_path / "start.sh"
    sh.write_bytes(b"#!/usr/bin/env bash\r\nset -e\r\necho hi\r\n")
    assert mod._payload(sh) == b"#!/usr/bin/env bash\nset -e\necho hi\n"
    bat = tmp_path / "START_HERE.bat"
    bat.write_bytes(b"@echo off\nset X=1\n")
    assert mod._payload(bat) == b"@echo off\r\nset X=1\r\n"
    py = tmp_path / "a.py"
    py.write_bytes(b"x = 1\r\n")
    assert mod._payload(py) == b"x = 1\n"
    png = tmp_path / "a.png"
    png.write_bytes(b"\x89PNG\r\n\x1a\n")
    assert mod._payload(png) == b"\x89PNG\r\n\x1a\n"


def test_release_zip_exec_bit_survives_a_windows_build(tmp_path, monkeypatch):
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "make_release_zip", ROOT / "scripts" / "make_release_zip.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    root = tmp_path / "fork"
    root.mkdir()
    (root / "pyproject.toml").write_text('version = "9.9.9"\n')
    (root / "start.sh").write_text("#!/usr/bin/env bash\necho hi\n")
    (root / "uninstall.sh").write_text("#!/usr/bin/env bash\necho bye\n")
    monkeypatch.setattr(sys, "platform", "win32")      # what ZipInfo looks at
    out = mod.build(root, tmp_path / "dist")
    for info in zipfile.ZipFile(out).infolist():
        assert info.create_system == 3, info.filename
        if info.filename.endswith(".sh"):
            assert (info.external_attr >> 16) & 0o111, info.filename


def test_release_zip_never_ships_a_ledger_or_a_secrets_file():
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "make_release_zip", ROOT / "scripts" / "make_release_zip.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    for rel in ("proxy/dlc_proxy.db", "proxy/dlc_proxy.db-journal",
                "proxy/dlc_proxy.db-wal", "data/anything.db",
                "proxy/.env", "proxy/.env.local", "dlc/.env"):
        assert mod._want(Path(rel)) is False, f"would ship {rel}"
    for rel in ("proxy/dlc_proxy.py", "proxy/README.md",
                "data/official_tests_defaults.json"):
        assert mod._want(Path(rel)) is True, f"would drop {rel}"
