"""NX journal job schema helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Any


NX_JOB_SCHEMA_VERSION = "fromcad2cfd_nx_job_v1"


@dataclass(frozen=True)
class NXJournalJob:
    """Serializable job request consumed by an NXOpen journal."""

    operation: str
    output_dir: str
    model_name: str
    parameters: dict[str, Any] = field(default_factory=dict)
    schema_version: str = NX_JOB_SCHEMA_VERSION
    input_file: str | None = None
    export_formats: tuple[str, ...] = ("PARASOLID",)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "operation": self.operation,
            "input_file": self.input_file,
            "output_dir": self.output_dir,
            "model_name": self.model_name,
            "parameters": self.parameters,
            "export_formats": list(self.export_formats),
            "metadata": self.metadata,
        }

    def write(self, path: str | Path) -> Path:
        output = Path(path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(self.to_dict(), ensure_ascii=True, indent=2), encoding="utf-8")
        return output


def read_job(path: str | Path) -> NXJournalJob:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if payload.get("schema_version") != NX_JOB_SCHEMA_VERSION:
        raise ValueError(f"Unsupported NX job schema: {payload.get('schema_version')}")
    return NXJournalJob(
        operation=payload["operation"],
        input_file=payload.get("input_file"),
        output_dir=payload["output_dir"],
        model_name=payload["model_name"],
        parameters=payload.get("parameters") or {},
        export_formats=tuple(payload.get("export_formats") or ("PARASOLID",)),
        metadata=payload.get("metadata") or {},
    )
