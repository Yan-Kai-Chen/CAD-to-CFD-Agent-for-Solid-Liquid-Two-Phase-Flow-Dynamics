# Result Schema

The framework tools return JSON-serializable dictionaries.

Common fields:

- `status`: `success`, `partial`, or `failed`.
- `timestamp`: local timestamp for generated artifacts.
- `outputs`: generated files with path, size, and export method.
- `errors`: list of blocking errors.
- `reports`: Markdown and JSON report paths.

SolidWorks operations should include rebuild and export status whenever geometry is changed.
