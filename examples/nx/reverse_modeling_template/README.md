# NX Reverse Modeling Template

This directory documents the public command template for the NX reverse-modeling
workflow. It intentionally does not include the private research geometry used
for local validation.

## Step 1: STL To Convergent PRT

```powershell
fromcad2cfd nx write-reverse-step1-stl-import-job --input-file sandbox\input\example_faceted_geometry.stl --project nx_reverse_step1_example
```

Expected private runtime output:

- copied STL in `05_projects/<project>/input/`
- NX `.prt` in `05_projects/<project>/output/`
- JSON and Markdown reports in `05_projects/<project>/reports/`

## Step 2: Cage From Facet Body

```powershell
fromcad2cfd nx write-reverse-step2-cage-from-facet-body-job --input-file sandbox\input\example_step1_convergent.prt --project nx_reverse_step2_example --average-size-mm 10
```

This command is a template. It requires a real Step 1 `.prt` created locally and
must not be run against a source file committed to the repository.

## Step 3/4: XOY Plane Combine

```powershell
fromcad2cfd nx write-reverse-step3-step4-xoz-plane-combine-job --input-file sandbox\input\example_reverse_model.x_t --project nx_reverse_step3_step4_example --square-size-mm 1000 --plane-offset-z-mm 5
```

The command name contains `xoz` for legacy compatibility. The validated
geometry is an XOY bounded-plane sheet centered at the origin and translated
`+5 mm` along global Z.

Step 4 uses `CombineSheetsBuilder` with explicit keep/remove region trackers.
That selector pattern was learned from a manual NX journal capture and converted
into controlled code.

## What Not To Commit

Do not commit:

- private STL files,
- NX `.prt` files,
- Parasolid `.x_t` or `.x_b` files,
- STEP/STP exports,
- generated reports from private geometry,
- raw recorded journals containing private paths or feature identifiers.

For the journal-capture method, see `docs/nx/manual_journal_capture.md`.
