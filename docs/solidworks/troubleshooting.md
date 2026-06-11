# SolidWorks Troubleshooting

## COM Connection Fails

- Confirm SolidWorks is installed.
- Confirm `pywin32` is installed.
- Try launching SolidWorks once manually.
- Set `SOLIDWORKS_EXE` if the executable is not in a common path.

## Template Not Found

Set `SOLIDWORKS_TEMPLATE_DIR` to the folder containing part templates.

## STEP Export Fails

Check rebuild status, output path length, and whether a file with the same name already exists.
