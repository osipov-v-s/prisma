$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$ServiceOutput = Join-Path $ProjectRoot "build\service"

& $Python -m pip install -e "${ProjectRoot}[service,desktop-build]"
& $Python -m PyInstaller --noconfirm --clean --onefile --name prisma-service `
    --paths $ProjectRoot `
    --add-data "$ProjectRoot\alembic.ini;." `
    --add-data "$ProjectRoot\migrations;migrations" `
    --collect-all reportlab `
    --collect-all openpyxl `
    --distpath $ServiceOutput `
    "$ProjectRoot\apps\service\prisma_service\desktop_entry.py"

Push-Location $ProjectRoot
try {
    pnpm desktop:package
}
finally {
    Pop-Location
}
