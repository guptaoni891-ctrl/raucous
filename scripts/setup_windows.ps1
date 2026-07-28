$ErrorActionPreference = "Stop"

if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
    throw "Python launcher 'py' was not found. Install Python 3.11 or newer."
}

py -m venv .venv
& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\python.exe -m pip install -e ".[dev]"

Write-Host ""
Write-Host "VinylPulse is installed."
Write-Host "Activate: .venv\Scripts\Activate.ps1"
Write-Host "Demo:    vinylpulse --demo"
Write-Host "Devices: vinylpulse --list-audio-devices"
