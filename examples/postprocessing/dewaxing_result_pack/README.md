# Dewaxing Result Pack Fixture

This directory contains a public-safe synthetic dewaxing Agent Result Pack.
It mirrors the private result-pack contract without including private Fluent
case/data files, CAD geometry, images, videos, or proprietary run directories.

Validate it with:

```powershell
python -m fromcad2cfd post validate-dewaxing-pack --pack examples/postprocessing/dewaxing_result_pack
```
