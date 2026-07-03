import { defineConfig } from "@playwright/test";
import path from "node:path";

const HERE = import.meta.dirname;
const BACKEND_DIR = path.resolve(HERE, "../backend");
const PYTHON = path.join(BACKEND_DIR, ".venv", "Scripts", "python.exe");

/** E2E на отдельной БД (e2e.sqlite3): globalSetup мигрирует и сидит заново. */
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  workers: 1,
  timeout: 45_000,
  // Сценарии мутируют seed-данные — повтор внутри прогона даёт ложные падения.
  retries: 0,
  globalSetup: "./e2e/global-setup.ts",
  use: {
    baseURL: "http://127.0.0.1:5173",
    trace: "retain-on-failure",
    locale: "ru-RU",
  },
  webServer: [
    {
      command: `"${PYTHON}" manage.py runserver 127.0.0.1:8000 --noreload`,
      cwd: BACKEND_DIR,
      env: { ARKAND_DB_NAME: "e2e.sqlite3" },
      url: "http://127.0.0.1:8000/admin/login/",
      reuseExistingServer: false,
      timeout: 120_000,
    },
    {
      command: "npx vite --port 5173 --strictPort",
      cwd: HERE,
      url: "http://127.0.0.1:5173",
      reuseExistingServer: false,
      timeout: 120_000,
    },
  ],
});
