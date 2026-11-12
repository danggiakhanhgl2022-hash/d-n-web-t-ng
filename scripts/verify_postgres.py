"""Run integration tests on a separate PostgreSQL database, never the user database."""
import os
from pathlib import Path
import subprocess
import sys
from manage import ROOT, ENV, PYTHON, load_env

load_env()
import psycopg
from psycopg import sql
from sqlalchemy.engine import make_url

url = make_url(ENV["DATABASE_URL"])
test_name = "video_os_stage01_tests"
assert test_name != url.database and test_name.endswith("_tests")
admin_url = url.set(drivername="postgresql", database="postgres").render_as_string(hide_password=False)
with psycopg.connect(admin_url, autocommit=True, connect_timeout=10) as connection:
    exists = connection.execute("SELECT 1 FROM pg_database WHERE datname=%s", (test_name,)).fetchone()
    if not exists:
        connection.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(test_name)))
test_url = url.set(database=test_name).render_as_string(hide_password=False)
test_env = ENV.copy()
test_env["STAGE01_TEST_DATABASE_URL"] = test_url
proof = ROOT / "runtime" / "verification"
proof.mkdir(parents=True, exist_ok=True)
with (proof / "postgres-tests.log").open("w", encoding="utf-8") as log:
    result = subprocess.run([str(PYTHON), "-m", "pytest", "-q", "--junitxml", str(proof / "postgres-tests.xml")],
                            cwd=ROOT, env=test_env, stdout=log, stderr=subprocess.STDOUT)
print(f"PostgreSQL isolated integration exit={result.returncode}; proof=runtime/verification/postgres-tests.log")
raise SystemExit(result.returncode)
