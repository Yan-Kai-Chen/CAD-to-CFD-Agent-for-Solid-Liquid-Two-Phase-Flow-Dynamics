"""Linear-system utilities for the unstructured FastFluent backend.

This module is intentionally dependency-free. It provides the small CSR and
solver layer needed for benchmark gates before a production sparse backend is
introduced.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import sqrt
from typing import Any, Iterable


LINEAR_SYSTEM_SCHEMA_VERSION = "fromcad2cfd_fastfluent_unstructured_linear_system_v1"


@dataclass(frozen=True)
class SparseMatrixCSR:
    """Minimal compressed sparse row matrix."""

    n_rows: int
    n_cols: int
    indptr: tuple[int, ...]
    indices: tuple[int, ...]
    data: tuple[float, ...]

    @classmethod
    def from_rows(cls, rows: Iterable[dict[int, float]], *, n_cols: int | None = None, drop_tolerance: float = 0.0) -> "SparseMatrixCSR":
        row_list = list(rows)
        n_rows = len(row_list)
        n_cols = n_cols if n_cols is not None else n_rows
        indptr = [0]
        indices: list[int] = []
        data: list[float] = []
        for row in row_list:
            for column, value in sorted(row.items()):
                if column < 0 or column >= n_cols:
                    raise ValueError(f"Sparse matrix column index out of range: {column}")
                if abs(value) <= drop_tolerance:
                    continue
                indices.append(int(column))
                data.append(float(value))
            indptr.append(len(indices))
        return cls(n_rows=n_rows, n_cols=n_cols, indptr=tuple(indptr), indices=tuple(indices), data=tuple(data))

    @classmethod
    def from_triplets(
        cls,
        n_rows: int,
        n_cols: int,
        triplets: Iterable[tuple[int, int, float]],
        *,
        drop_tolerance: float = 0.0,
    ) -> "SparseMatrixCSR":
        rows = [dict() for _ in range(n_rows)]
        for row, column, value in triplets:
            if row < 0 or row >= n_rows:
                raise ValueError(f"Sparse matrix row index out of range: {row}")
            if column < 0 or column >= n_cols:
                raise ValueError(f"Sparse matrix column index out of range: {column}")
            rows[row][column] = rows[row].get(column, 0.0) + float(value)
        return cls.from_rows(rows, n_cols=n_cols, drop_tolerance=drop_tolerance)

    @property
    def shape(self) -> tuple[int, int]:
        return (self.n_rows, self.n_cols)

    @property
    def nnz(self) -> int:
        return len(self.data)

    def matvec(self, values: list[float] | tuple[float, ...]) -> list[float]:
        if len(values) != self.n_cols:
            raise ValueError(f"Matrix-vector size mismatch: matrix has {self.n_cols} columns, vector has {len(values)} values.")
        result: list[float] = []
        for row in range(self.n_rows):
            start = self.indptr[row]
            end = self.indptr[row + 1]
            result.append(sum(self.data[item] * values[self.indices[item]] for item in range(start, end)))
        return result

    def diagonal(self) -> list[float]:
        diagonal = [0.0 for _ in range(min(self.n_rows, self.n_cols))]
        for row in range(self.n_rows):
            for item in range(self.indptr[row], self.indptr[row + 1]):
                column = self.indices[item]
                if row == column and row < len(diagonal):
                    diagonal[row] = self.data[item]
                    break
        return diagonal

    def to_dense(self) -> list[list[float]]:
        dense = [[0.0 for _ in range(self.n_cols)] for _ in range(self.n_rows)]
        for row in range(self.n_rows):
            for item in range(self.indptr[row], self.indptr[row + 1]):
                dense[row][self.indices[item]] += self.data[item]
        return dense

    def metadata(self) -> dict[str, Any]:
        total = self.n_rows * self.n_cols
        return {
            "schema_version": LINEAR_SYSTEM_SCHEMA_VERSION,
            "storage": "csr",
            "n_rows": self.n_rows,
            "n_cols": self.n_cols,
            "nnz": self.nnz,
            "density": self.nnz / total if total else 0.0,
        }


@dataclass(frozen=True)
class LinearSolveResult:
    """Result envelope for a deterministic linear solve."""

    method: str
    values: list[float]
    converged: bool
    iterations: int
    tolerance: float
    initial_residual_l2: float
    initial_residual_linf: float
    final_residual_l2: float
    final_residual_linf: float
    residual_history: list[dict[str, float]]

    def metadata(self, matrix: SparseMatrixCSR) -> dict[str, Any]:
        payload = matrix.metadata()
        payload.update(
            {
                "method": self.method,
                "converged": self.converged,
                "iterations": self.iterations,
                "tolerance": self.tolerance,
                "initial_residual_l2": self.initial_residual_l2,
                "initial_residual_linf": self.initial_residual_linf,
                "final_residual_l2": self.final_residual_l2,
                "final_residual_linf": self.final_residual_linf,
            }
        )
        return payload


def solve_linear_system(
    matrix: SparseMatrixCSR,
    rhs: list[float],
    *,
    method: str = "sparse_cg",
    tolerance: float = 1.0e-12,
    max_iterations: int | None = None,
) -> LinearSolveResult:
    """Solve a linear system with an allowed local method."""

    normalized = method.replace("-", "_")
    if normalized == "dense_direct":
        return solve_dense_direct(matrix, rhs, tolerance=tolerance)
    if normalized == "sparse_cg":
        return solve_sparse_cg(matrix, rhs, tolerance=tolerance, max_iterations=max_iterations)
    raise ValueError(f"Unsupported unstructured linear solver method: {method}")


def solve_dense_direct(matrix: SparseMatrixCSR, rhs: list[float], *, tolerance: float = 1.0e-12) -> LinearSolveResult:
    dense = matrix.to_dense()
    initial = residual_norms(matrix, rhs, [0.0 for _ in rhs])
    values = _gaussian_elimination(dense, rhs)
    final = residual_norms(matrix, rhs, values)
    return LinearSolveResult(
        method="dense_direct",
        values=values,
        converged=final["l2"] <= tolerance * max(1.0, _l2_norm(rhs)),
        iterations=1,
        tolerance=tolerance,
        initial_residual_l2=initial["l2"],
        initial_residual_linf=initial["linf"],
        final_residual_l2=final["l2"],
        final_residual_linf=final["linf"],
        residual_history=[
            {"iteration": 0, "residual_l2": initial["l2"], "residual_linf": initial["linf"]},
            {"iteration": 1, "residual_l2": final["l2"], "residual_linf": final["linf"]},
        ],
    )


def solve_sparse_cg(
    matrix: SparseMatrixCSR,
    rhs: list[float],
    *,
    tolerance: float = 1.0e-12,
    max_iterations: int | None = None,
) -> LinearSolveResult:
    if matrix.n_rows != matrix.n_cols:
        raise ValueError("Sparse CG requires a square matrix.")
    if len(rhs) != matrix.n_rows:
        raise ValueError(f"Right-hand side length mismatch: matrix has {matrix.n_rows} rows, rhs has {len(rhs)} values.")
    diagonal = matrix.diagonal()
    if any(abs(value) < 1.0e-30 for value in diagonal):
        raise ValueError("Sparse CG requires non-zero diagonal entries for the current gate.")
    limit = max_iterations if max_iterations is not None else max(20, matrix.n_rows * 20)
    x = [0.0 for _ in rhs]
    ax = matrix.matvec(x)
    r = [target - value for target, value in zip(rhs, ax)]
    p = list(r)
    rs_old = _dot(r, r)
    initial = _norms(r)
    threshold = tolerance * max(1.0, _l2_norm(rhs))
    history = [{"iteration": 0, "residual_l2": initial["l2"], "residual_linf": initial["linf"]}]
    if initial["l2"] <= threshold:
        return LinearSolveResult(
            method="sparse_cg",
            values=x,
            converged=True,
            iterations=0,
            tolerance=tolerance,
            initial_residual_l2=initial["l2"],
            initial_residual_linf=initial["linf"],
            final_residual_l2=initial["l2"],
            final_residual_linf=initial["linf"],
            residual_history=history,
        )
    converged = False
    final = initial
    iteration = 0
    for iteration in range(1, limit + 1):
        ap = matrix.matvec(p)
        denominator = _dot(p, ap)
        if abs(denominator) < 1.0e-30:
            break
        alpha = rs_old / denominator
        x = [value + alpha * direction for value, direction in zip(x, p)]
        r = [residual - alpha * value for residual, value in zip(r, ap)]
        final = _norms(r)
        history.append({"iteration": iteration, "residual_l2": final["l2"], "residual_linf": final["linf"]})
        if final["l2"] <= threshold:
            converged = True
            break
        rs_new = _dot(r, r)
        if rs_old <= 0:
            break
        beta = rs_new / rs_old
        p = [residual + beta * direction for residual, direction in zip(r, p)]
        rs_old = rs_new
    return LinearSolveResult(
        method="sparse_cg",
        values=x,
        converged=converged,
        iterations=iteration,
        tolerance=tolerance,
        initial_residual_l2=initial["l2"],
        initial_residual_linf=initial["linf"],
        final_residual_l2=final["l2"],
        final_residual_linf=final["linf"],
        residual_history=history,
    )


def residual_norms(matrix: SparseMatrixCSR, rhs: list[float], values: list[float]) -> dict[str, float]:
    ax = matrix.matvec(values)
    residuals = [left - target for left, target in zip(ax, rhs)]
    return _norms(residuals)


def _gaussian_elimination(matrix: list[list[float]], rhs: list[float]) -> list[float]:
    size = len(rhs)
    augmented = [list(row) + [rhs[index]] for index, row in enumerate(matrix)]
    for column in range(size):
        pivot_row = max(range(column, size), key=lambda row: abs(augmented[row][column]))
        pivot = augmented[pivot_row][column]
        if abs(pivot) < 1.0e-14:
            raise ValueError("Linear system is singular or ill-conditioned for the current gate.")
        if pivot_row != column:
            augmented[column], augmented[pivot_row] = augmented[pivot_row], augmented[column]
        scale = augmented[column][column]
        for item in range(column, size + 1):
            augmented[column][item] /= scale
        for row in range(size):
            if row == column:
                continue
            factor = augmented[row][column]
            for item in range(column, size + 1):
                augmented[row][item] -= factor * augmented[column][item]
    return [augmented[row][size] for row in range(size)]


def _norms(values: list[float]) -> dict[str, float]:
    return {
        "l2": _l2_norm(values),
        "linf": max((abs(value) for value in values), default=0.0),
    }


def _l2_norm(values: list[float]) -> float:
    return sqrt(sum(value * value for value in values))


def _dot(left: list[float], right: list[float]) -> float:
    return sum(a * b for a, b in zip(left, right))
