"""NX expression edit placeholders."""

from __future__ import annotations

from fromcad2cfd_cad import AgentResult, ParameterEditRequest


def safe_edit_expression_placeholder(request: ParameterEditRequest) -> AgentResult:
    return AgentResult(
        status="skipped",
        backend="nx",
        operation="edit_parameter_by_exact_name",
        message="NX expression editing is planned but not enabled in the scaffold.",
        outputs={
            "input_file": request.input_file,
            "parameter_name": request.parameter_name,
            "value_mm": request.value_mm,
            "output_dir": request.output_dir,
        },
    )
