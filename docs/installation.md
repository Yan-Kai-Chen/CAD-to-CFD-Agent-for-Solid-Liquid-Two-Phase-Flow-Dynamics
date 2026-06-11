# Installation

## Requirements

- Windows.
- SolidWorks with COM registration.
- Python 3.10 or newer.

## Development Install

```powershell
python -m pip install -e ".[dev]"
```

## SolidWorks Path Configuration

The package tries common SolidWorks installation and template paths. You can override them:

```powershell
$env:SOLIDWORKS_EXE="C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS\SLDWORKS.exe"
$env:SOLIDWORKS_TEMPLATE_DIR="C:\ProgramData\SOLIDWORKS\SOLIDWORKS 2025\templates"
```
