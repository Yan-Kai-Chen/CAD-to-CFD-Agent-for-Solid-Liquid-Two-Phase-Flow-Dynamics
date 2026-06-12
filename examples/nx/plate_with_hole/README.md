# NX Plate With Hole Job

This example is a backend-neutral synthetic job payload. It is safe to publish
because it does not include private geometry and does not run NX by itself.

```powershell
fromcad2cfd nx write-job --recipe plate-with-hole
```

Use this as a schema reference. Generated CAD and report outputs should stay
under ignored runtime folders.
