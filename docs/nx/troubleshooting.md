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

## The MCP server is only a scaffold

This is expected. The safe MCP wrapper should be wired only after the backend
preflight, job schema, and journal runner are stable.
