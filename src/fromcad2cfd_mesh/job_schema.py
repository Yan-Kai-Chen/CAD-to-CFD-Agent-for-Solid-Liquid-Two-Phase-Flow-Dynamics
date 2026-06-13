"""Job schema for mesh preprocessing workflows."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Any


MESH_JOB_SCHEMA_VERSION = "fromcad2cfd_mesh_job_v1"


@dataclass(frozen=True)
class MeshJob:
    """Serializable mesh workflow request."""

    operation: str
    input_file: str
    output_dir: str
    model_name: str
    parameters: dict[str, Any] = field(default_factory=dict)
    schema_version: str = MESH_JOB_SCHEMA_VERSION
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "operation": self.operation,
            "input_file": self.input_file,
            "output_dir": self.output_dir,
            "model_name": self.model_name,
            "parameters": self.parameters,
            "metadata": self.metadata,
        }

    def write(self, path: str | Path) -> Path:
        output = Path(path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(self.to_dict(), ensure_ascii=True, indent=2), encoding="utf-8")
        return output


def read_mesh_job(path: str | Path) -> MeshJob:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if payload.get("schema_version") != MESH_JOB_SCHEMA_VERSION:
        raise ValueError(f"Unsupported mesh job schema: {payload.get('schema_version')}")
    return MeshJob(
        operation=payload["operation"],
        input_file=payload["input_file"],
        output_dir=payload["output_dir"],
        model_name=payload["model_name"],
        parameters=payload.get("parameters") or {},
        metadata=payload.get("metadata") or {},
    )
