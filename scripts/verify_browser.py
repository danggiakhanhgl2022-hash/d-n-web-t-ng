"""Launch isolated PostgreSQL + local servers for browser acceptance, then stop QA servers."""
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import time
import uuid
from manage import ROOT, ENV, PYTHON, NPM, load_env, ready

load_env()
import psycopg
from psycopg import sql
from sqlalchemy.engine import make_url

if ready("http://127.0.0.1:8100/api/v1/health") or ready("http://127.0.0.1:3100"):
    raise SystemExit("Ports 8100/3100 are in use. Stop the owned app before isolated browser verification.")

url = make_url(ENV["DATABASE_URL"])
name = "video_os_stage01_browser_" + uuid.uuid4().hex[:8]
with psycopg.connect(url.set(drivername="postgresql", database="postgres").render_as_string(hide_password=False), autocommit=True, connect_timeout=10) as db:
    db.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
qa_env = ENV.copy()
qa_env["DATABASE_URL"] = url.set(database=name).render_as_string(hide_password=False)
qa_env["STORAGE_DIR"] = str(ROOT / "runtime" / name)
qa_env["STAGE01_BROWSER_QA"] = "1"
qa_env["STAGE01_BROWSER_PASSWORD"] = secrets.token_urlsafe(24)
proof = ROOT / "runtime" / "browser-qa"
proof.mkdir(parents=True, exist_ok=True)
subprocess.run([str(PYTHON), "-m", "alembic", "-c", "alembic.ini", "upgrade", "head"],
               cwd=ROOT / "backend", env=qa_env, check=True)
subprocess.run([str(PYTHON), "-m", "app.bootstrap", "--username", "qa-browser-owner", "--display-name", "QA Browser Owner",
                "--tenant-name", "QA browser — not customer", "--password-stdin"],
               input=qa_env["STAGE01_BROWSER_PASSWORD"] + "\n", text=True,
               stdout=subprocess.DEVNULL, cwd=ROOT / "backend", env=qa_env, check=True)

processes = []
try:
    commands = [
        ("backend", [str(PYTHON), "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8100"], ROOT / "backend", "http://127.0.0.1:8100/api/v1/health"),
        ("frontend", [NPM, "run", "start"], ROOT / "frontend", "http://127.0.0.1:3100"),
    ]
    for label, command, cwd, endpoint in commands:
        with (proof / f"{label}.log").open("ab") as log:
            child = subprocess.Popen(command, cwd=cwd, env=qa_env, stdin=subprocess.DEVNULL,
                                     stdout=log, stderr=subprocess.STDOUT,
                                     creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
        processes.append(child)
        until = time.time() + 90
        while time.time() < until:
            if child.poll() is not None:
                raise RuntimeError(f"QA {label} stopped; inspect runtime/browser-qa/{label}.log")
            if ready(endpoint):
                break
            time.sleep(0.5)
        else:
            raise RuntimeError(f"QA {label} did not start")
    run = subprocess.run([str(PYTHON), ROOT / "scripts" / "browser_check.py"], cwd=ROOT, env=qa_env)
    (proof / "isolation.json").write_text(json.dumps({"qa_database": name, "main_database_used": False, "exit_code": run.returncode}, indent=2), encoding="utf-8")
    if run.returncode:
        raise SystemExit(run.returncode)
finally:
    for child in reversed(processes):
        if child.poll() is None:
            if os.name == "nt":
                subprocess.run(["taskkill", "/PID", str(child.pid), "/T", "/F"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                child.terminate()
                child.wait(timeout=15)
