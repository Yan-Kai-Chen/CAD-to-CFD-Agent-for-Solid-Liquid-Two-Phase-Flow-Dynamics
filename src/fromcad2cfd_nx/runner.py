"""Safe NX journal runner command construction."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import subprocess
from typing import Sequence

from fromcad2cfd_cad import AgentResult

from .job_schema import NXJournalJob
from .preflight import detect_nx_environment


@dataclass(frozen=True)
class NXJournalCommand:
    """Prepared command for NX journal execution."""

    run_journal: str
    journal_path: str
    job_path: str

    def argv(self) -> list[str]:
        return [self.run_journal, self.journal_path, "-args", self.job_path]


def prepare_journal_command(job_path: str | Path, journal_path: str | Path, *, run_journal: str | None = None) -> NXJournalCommand:
    report = detect_nx_environment()
    runner = run_journal or report.run_journal
    if not runner:
        raise RuntimeError("run_journal.exe was not found. Run `fromcad2cfd nx preflight` first.")
    journal = Path(journal_path)
    job = Path(job_path)
    if not journal.exists():
        raise FileNotFoundError(f"NX journal does not exist: {journal}")
    if not job.exists():
        raise FileNotFoundError(f"NX job file does not exist: {job}")
    return NXJournalCommand(run_journal=str(runner), journal_path=str(journal), job_path=str(job))


def run_journal_command(command: NXJournalCommand, *, timeout_sec: int = 240, execute: bool = False) -> AgentResult:
    """Run a prepared NX journal command only when execution is explicitly enabled."""

    if not execute:
        return AgentResult(
            status="skipped",
            backend="nx",
            operation="run_journal",
            message="Journal execution was skipped because execute=False.",
            outputs={"command": command.argv()},
        )

    completed = subprocess.run(
        command.argv(),
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout_sec,
    )
    status = "success" if completed.returncode == 0 else "failed"
    return AgentResult(
        status=status,
        backend="nx",
        operation="run_journal",
        message="NX journal command completed.",
        outputs={
            "command": command.argv(),
            "returncode": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
        },
        errors=[] if completed.returncode == 0 else [completed.stderr or f"Return code {completed.returncode}"],
    )


def write_job_and_prepare_command(
    job: NXJournalJob,
    *,
    job_path: str | Path,
    journal_path: str | Path,
    run_journal: str | None = None,
) -> NXJournalCommand:
    job.write(job_path)
    return prepare_journal_command(job_path=job_path, journal_path=journal_path, run_journal=run_journal)
