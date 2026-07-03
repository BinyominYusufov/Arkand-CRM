# ARKAND · Финансовый модуль — запуск одной командой.
# Поднимает backend (Django, SQLite) и frontend (Vite) в отдельных окнах.
# Первая настройка: venv, зависимости, миграции, seed — всё автоматически.
$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
$backend = Join-Path $root "backend"
$frontend = Join-Path $root "frontend"
$python = Join-Path $backend ".venv\Scripts\python.exe"

if (-not (Test-Path $python)) {
    Write-Host "Создаю venv и ставлю зависимости backend..." -ForegroundColor Cyan
    python -m venv (Join-Path $backend ".venv")
    & $python -m pip install --upgrade pip -q
    & $python -m pip install -r (Join-Path $backend "requirements.txt") -q
}

Write-Host "Миграции..." -ForegroundColor Cyan
& $python (Join-Path $backend "manage.py") migrate

$db = Join-Path $backend "db.sqlite3"
$needSeed = & $python (Join-Path $backend "manage.py") shell -c "from apps.core.models import User; print('EMPTY' if not User.objects.exists() else 'OK')"
if ($needSeed -match "EMPTY") {
    Write-Host "Наполняю демо-данными (seed_demo)..." -ForegroundColor Cyan
    & $python (Join-Path $backend "manage.py") seed_demo
}

if (-not (Test-Path (Join-Path $frontend "node_modules"))) {
    Write-Host "Ставлю зависимости frontend..." -ForegroundColor Cyan
    Push-Location $frontend; npm install --no-fund --no-audit; Pop-Location
}

Write-Host "Стартую backend (http://127.0.0.1:8000) и frontend (http://127.0.0.1:5173)..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$backend'; & '$python' manage.py runserver"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$frontend'; npm run dev"

Write-Host ""
Write-Host "Готово. Откройте http://127.0.0.1:5173" -ForegroundColor Green
Write-Host "Пользователи (пароль arkand2026): nigina@arkand.tj (главбух), firuz@/manizha@ (бухгалтеры),"
Write-Host "jamshed@/farrukh@/sino@/dilnoza@ (кассиры), owner@/umed@ (владельцы), rustam@ (менеджер)."
