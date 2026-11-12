"""Local project launcher. No production approval or generation is performed."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import re
import secrets
import subprocess
import sys
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
PYTHON = ROOT / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
NPM = "npm.cmd" if os.name == "nt" else "npm"
ENV = os.environ.copy()
ENV["PYTHONPATH"] = str(ROOT / "backend")
ENV["PYTHONUTF8"] = "1"
ENV["NEXT_TELEMETRY_DISABLED"] = "1"
ENV["npm_config_cache"] = str(ROOT.parent / ".npm-cache")
BUILD_POINTER = ROOT / "runtime" / "frontend-build.json"
LEGACY_BUILD = ".next-v6"


def active_build():
    if not BUILD_POINTER.exists():
        return LEGACY_BUILD
    data = json.loads(BUILD_POINTER.read_text(encoding="utf-8"))
    name = data.get("directory", "")
    if not isinstance(name, str) or not re.fullmatch(r"\.next-build-[0-9a-f]{12}", name):
        raise RuntimeError("Invalid frontend build metadata; refusing to use an unexpected path.")
    return name


def build_frontend():
    # Never ask Next to clean a directory that another Windows process may
    # still hold open. Keep the previous build and pointer if compilation fails.
    name = ".next-build-" + secrets.token_hex(6)
    env = ENV.copy()
    env["VIDEO_OS_NEXT_DIST_DIR"] = name
    # Next adds build-specific paths to its tsconfig. A temporary config keeps
    # repeated builds from editing the user's tsconfig on every update.
    tsconfig = ROOT / "frontend" / f"{name}.tsconfig.json"
    env["VIDEO_OS_NEXT_TSCONFIG"] = tsconfig.name
    tsconfig.write_text(json.dumps({"extends": "./tsconfig.json", "include": [
        "next-env.d.ts", "**/*.ts", "**/*.tsx",
        f"{name}/types/**/*.ts", f"{name}/dev/types/**/*.ts",
    ]}, indent=2), encoding="utf-8")
    try:
        subprocess.run([NPM, "run", "build"], cwd=ROOT / "frontend", env=env, check=True)
    finally:
        try:
            tsconfig.unlink(missing_ok=True)
        except OSError:
            print(f"Temporary build config could not be removed: {tsconfig.name}")
    if not (ROOT / "frontend" / name / "BUILD_ID").is_file():
        raise RuntimeError("Frontend build did not produce BUILD_ID; the previous build is retained.")
    BUILD_POINTER.parent.mkdir(parents=True, exist_ok=True)
    temp = BUILD_POINTER.with_suffix(".tmp")
    temp.write_text(json.dumps({"directory": name}), encoding="utf-8")
    temp.replace(BUILD_POINTER)
    print(f"Frontend build ready: {name}", flush=True)


def load_env():
    path = ROOT / ".env"
    if path.exists():
        for line in path.read_text(encoding="utf-8-sig").splitlines():
            if line.strip() and not line.lstrip().startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                ENV[key.strip()] = value.strip()


def execute(args, cwd=ROOT, **kwargs):
    return subprocess.run([str(a) for a in args], cwd=cwd, env=ENV, check=True, **kwargs)


def configure():
    if not (ROOT / ".env.postgres").exists():
        password = secrets.token_hex(32)
        (ROOT / ".env.postgres").write_text(
            f"POSTGRES_USER=video_os\nPOSTGRES_DB=video_os\nPOSTGRES_PASSWORD={password}\n", encoding="utf-8"
        )
    if not (ROOT / ".env").exists():
        entries = dict(line.split("=", 1) for line in (ROOT / ".env.postgres").read_text(encoding="utf-8").splitlines() if "=" in line)
        (ROOT / ".env").write_text(
            f"DATABASE_URL=postgresql+psycopg://video_os:{entries['POSTGRES_PASSWORD']}@127.0.0.1:54329/video_os\n"
            f"STORAGE_DIR={ROOT / 'runtime' / 'storage'}\n", encoding="utf-8"
        )
    load_env()


def setup():
    configure()
    if not PYTHON.exists():
        execute([sys.executable, "-m", "venv", ROOT / ".venv"])
    execute([PYTHON, "-m", "pip", "install", "--disable-pip-version-check", "-r", ROOT / "requirements.lock.txt"])
    execute([NPM, "ci", "--cache", ENV["npm_config_cache"]], cwd=ROOT / "frontend")
    build_frontend()
    existing = subprocess.run(["docker", "inspect", "--format", "{{.Config.Image}}", "video-os-stage1-db"],
                              stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
    if existing.returncode == 0:
        if not existing.stdout.strip().startswith("postgres:17"):
            raise RuntimeError("Container name is occupied by another image; refusing to change it.")
        execute(["docker", "start", "video-os-stage1-db"])
    else:
        execute(["docker", "compose", "up", "-d", "db"])
    deadline = time.time() + 90
    while time.time() < deadline:
        ready = subprocess.run(["docker", "exec", "video-os-stage1-db", "pg_isready", "-U", "video_os", "-d", "video_os"],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if ready.returncode == 0:
            break
        time.sleep(2)
    else:
        raise RuntimeError("PostgreSQL chua san sang; kiem tra Docker Desktop.")
    migrate()
    execute([PYTHON, ROOT / "scripts" / "init_owner.py"])
    print("Dependencies, database and local owner ready. Login file: TAI-KHOAN-CUC-BO.txt")


def migrate():
    load_env()
    execute([PYTHON, "-m", "alembic", "-c", "alembic.ini", "upgrade", "head"], cwd=ROOT / "backend")


def ready(url):
    try:
        with urllib.request.urlopen(url, timeout=2) as response:
            return response.status == 200
    except Exception:
        return False


def ensure_database():
    from sqlalchemy.engine import make_url
    import psycopg
    url = make_url(ENV["DATABASE_URL"])
    if url.drivername.startswith("sqlite"):
        return
    def connected():
        try:
            with psycopg.connect(url.set(drivername="postgresql").render_as_string(hide_password=False), connect_timeout=3):
                return True
        except psycopg.Error:
            return False
    if connected():
        return
    if url.host not in {"127.0.0.1", "localhost"} or url.database != "video_os":
        raise RuntimeError("Configured database is unavailable; no remote settings were changed.")
    execute(["docker", "start", "video-os-stage1-db"])
    until = time.time() + 60
    while time.time() < until:
        if connected():
            return
        time.sleep(1)
    raise RuntimeError("Local PostgreSQL is unavailable. Check Docker Desktop and local database configuration.")


def start():
    configure()
    ensure_database()
    build = active_build()
    if not (ROOT / "frontend" / build / "BUILD_ID").exists():
        build_frontend()
        build = active_build()
    ENV["VIDEO_OS_NEXT_DIST_DIR"] = build
    runtime = ROOT / "runtime"
    runtime.mkdir(exist_ok=True)
    commands = [
        ("backend", "http://127.0.0.1:8100/api/v1/health",
         [str(PYTHON), "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8100"], ROOT / "backend"),
        ("frontend", "http://127.0.0.1:3100",
         [NPM, "run", "start"], ROOT / "frontend"),
    ]
    pids = {}
    pidfile = runtime / "processes.json"
    if pidfile.exists():
        try:
            pids = json.loads(pidfile.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            pass
    for name, url, command, cwd in commands:
        if ready(url):
            print(f"{name}: already responding")
            continue
        with (runtime / f"{name}.log").open("ab") as log:
            child = subprocess.Popen(command, cwd=cwd, env=ENV, stdin=subprocess.DEVNULL,
                                     stdout=log, stderr=subprocess.STDOUT,
                                     creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                                     start_new_session=os.name != "nt")
        pids[name] = child.pid
        deadline = time.time() + 90
        while time.time() < deadline:
            if child.poll() is not None:
                raise RuntimeError(f"{name} stopped. Read runtime/{name}.log")
            if ready(url):
                break
            time.sleep(1)
        else:
            raise RuntimeError(f"{name} not ready. Read runtime/{name}.log")
        pidfile.write_text(json.dumps(pids), encoding="utf-8")
    print("Open http://127.0.0.1:3100 - Stage 01 local")
    print("Logs: runtime/backend.log and runtime/frontend.log")


def stop():
    pidfile = ROOT / "runtime" / "processes.json"
    if not pidfile.exists():
        print("No managed processes.")
        return
    pids = json.loads(pidfile.read_text(encoding="utf-8"))
    for name, pid in pids.items():
        if os.name == "nt":
            subprocess.run(["taskkill", "/PID", str(int(pid)), "/T", "/F"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            import signal
            try:
                os.killpg(int(pid), signal.SIGTERM)
            except ProcessLookupError:
                pass
        print(f"Stopped managed {name}. Database and data preserved.")
    # The managed Windows workspace permits updating this file but may deny
    # unlink. Empty metadata also cleanly records that no owned server remains.
    pidfile.write_text("{}", encoding="utf-8")


def update():
    configure()
    print("[1/3] Building into a new frontend directory...", flush=True)
    build_frontend()
    print("[2/3] Stopping managed app; database and data are preserved...", flush=True)
    stop()
    print("[3/3] Starting the updated app...", flush=True)
    start()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["setup", "migrate", "start", "stop", "update", "test"])
    args = parser.parse_args()
    load_env()
    if args.command == "test":
        execute([PYTHON, "-m", "pytest"])
    else:
        globals()[args.command]()


if __name__ == "__main__":
    main()

