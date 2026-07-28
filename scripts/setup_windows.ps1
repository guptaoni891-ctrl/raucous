$ErrorActionPreference = "Stop"

if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
    throw "Python launcher 'py' was not found. Install Python 3.11 or newer."
}

py -m venv .venv
& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\python.exe -m pip install -e ".[dev]"

Write-Host ""
Write-Host "Raucous is installed."
Write-Host "Activate: .venv\Scripts\Activate.ps1"
Write-Host "Demo:    raucous --demo"
Write-Host "Devices: raucous --list-audio-devices"
