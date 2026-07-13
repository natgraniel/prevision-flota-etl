param(
    [string]$Python = ".\venv\Scripts\python.exe"
)

$ErrorActionPreference = "Stop"

& $Python -m pip install pyinstaller
& $Python -m PyInstaller --noconfirm --clean --windowed --name "ProgramaETL" --paths "." "src\gui\app.py"

Write-Host "Ejecutable creado en dist\ProgramaETL\ProgramaETL.exe"
