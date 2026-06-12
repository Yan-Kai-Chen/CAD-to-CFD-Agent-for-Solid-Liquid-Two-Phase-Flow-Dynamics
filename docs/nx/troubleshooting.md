# Siemens NX Troubleshooting

## `run_journal.exe` is not detected

Check whether NX is installed and whether one of these paths exists:

```text
<NX base>/NXBIN/run_journal.exe
```

The preflight also checks common Windows locations and NX-related environment
variables.

## `UGII_BASE_DIR` does not match the detected installation

This means the environment variable points to a different NX installation than
the one found through local path probing. Keep the warning in the preflight
report and avoid journal execution until the intended NX installation is clear.

## The MCP server does not expose a requested raw operation

This is expected. The MCP server exposes only high-level safe tools. It does
not expose raw NXOpen calls, arbitrary journal replay, arbitrary Python
execution, file deletion, or overwrite operations.

Use the CLI job builders directly when an operation is intentionally outside the
MCP safe surface:

```powershell
fromcad2cfd nx write-basic-solid-pack-job
```
