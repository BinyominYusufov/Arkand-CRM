import { execFileSync } from "node:child_process";
import { existsSync, rmSync } from "node:fs";
import path from "node:path";

/** Свежая E2E-база: миграции + seed_demo (фиксированный Faker-seed). */
export default function globalSetup() {
  const backend = path.resolve(import.meta.dirname, "../../backend");
  const python = path.join(backend, ".venv", "Scripts", "python.exe");
  const env = { ...process.env, ARKAND_DB_NAME: "e2e.sqlite3" };

  for (const suffix of ["", "-wal", "-shm"]) {
    const dbPath = path.join(backend, `e2e.sqlite3${suffix}`);
    if (existsSync(dbPath)) rmSync(dbPath);
  }
  execFileSync(python, ["manage.py", "migrate", "--run-syncdb"], {
    cwd: backend,
    env,
    stdio: "inherit",
  });
  execFileSync(python, ["manage.py", "seed_demo"], {
    cwd: backend,
    env,
    stdio: "inherit",
  });
}
