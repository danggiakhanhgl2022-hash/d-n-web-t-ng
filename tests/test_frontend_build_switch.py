"""A failed frontend build must not replace the last usable build."""
import importlib.util
import json
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/manage.py'
spec = importlib.util.spec_from_file_location('video_os_manage', SCRIPT)
manage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(manage)


def test_build_switch_preserves_previous_build_on_failure(tmp_path, monkeypatch):
    frontend = tmp_path / 'frontend'
    frontend.mkdir()
    pointer = tmp_path / 'runtime/frontend-build.json'
    pointer.parent.mkdir()
    pointer.write_text(json.dumps({'directory': '.next-build-111111111111'}), encoding='utf-8')
    monkeypatch.setattr(manage, 'ROOT', tmp_path)
    monkeypatch.setattr(manage, 'BUILD_POINTER', pointer)
    monkeypatch.setattr(manage.secrets, 'token_hex', lambda _: '222222222222')

    def failed(*args, **kwargs):
        raise subprocess.CalledProcessError(1, args[0])
    monkeypatch.setattr(manage.subprocess, 'run', failed)
    with pytest.raises(subprocess.CalledProcessError):
        manage.build_frontend()
    assert manage.active_build() == '.next-build-111111111111'

    def success(args, cwd, env, check):
        assert env['VIDEO_OS_NEXT_DIST_DIR'] == '.next-build-222222222222'
        target = cwd / env['VIDEO_OS_NEXT_DIST_DIR']
        target.mkdir()
        (target / 'BUILD_ID').write_text('test', encoding='utf-8')
    monkeypatch.setattr(manage.subprocess, 'run', success)
    manage.build_frontend()
    assert manage.active_build() == '.next-build-222222222222'


def test_rejects_unexpected_build_path(tmp_path, monkeypatch):
    pointer = tmp_path / 'frontend-build.json'
    pointer.write_text(json.dumps({'directory': '../outside'}), encoding='utf-8')
    monkeypatch.setattr(manage, 'BUILD_POINTER', pointer)
    with pytest.raises(RuntimeError):
        manage.active_build()
