"""Shared helper for tracking pipeline stage runs: timing, logging, and a metadata CSV."""

import csv
import time
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
METADATA_PATH = PROJECT_ROOT / "output" / "quality_report" / "pipeline_metadata.csv"
METADATA_FIELDS = [
    "stage_name",
    "city",
    "timestamp",
    "row_count_in",
    "row_count_out",
    "status",
    "duration_seconds",
]


def append_metadata_row(
    stage_name: str,
    city: str,
    row_count_in: int | None,
    row_count_out: int | None,
    status: str,
    duration_seconds: float,
) -> None:
    METADATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    is_new_file = not METADATA_PATH.exists()

    with open(METADATA_PATH, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=METADATA_FIELDS)
        if is_new_file:
            writer.writeheader()
        writer.writerow(
            {
                "stage_name": stage_name,
                "city": city,
                "timestamp": datetime.now().isoformat(timespec="seconds"),
                "row_count_in": row_count_in if row_count_in is not None else "",
                "row_count_out": row_count_out if row_count_out is not None else "",
                "status": status,
                "duration_seconds": f"{duration_seconds:.3f}",
            }
        )


@dataclass
class StageResult:
    row_count_out: int | None = None


@contextmanager
def track_stage(logger, stage_name: str, city: str, row_count_in: int | None = None):
    """Time a pipeline stage, log its start/success/failure, and record a metadata row.

    The body's exceptions are caught here just long enough to log them and
    write a status="failed" metadata row, then re-raised -- this makes
    failures visible in logs/ and pipeline_metadata.csv without silently
    swallowing them, so the process still exits non-zero on a real failure.
    Set `result.row_count_out` inside the `with` block once the stage knows it.
    """
    start = time.perf_counter()
    result = StageResult()
    status = "success"

    logger.info(f"START stage={stage_name} city={city}")
    try:
        yield result
    except Exception:
        status = "failed"
        logger.exception(f"FAILURE stage={stage_name} city={city}")
        raise
    else:
        logger.info(f"SUCCESS stage={stage_name} city={city} row_count_out={result.row_count_out}")
    finally:
        duration_seconds = time.perf_counter() - start
        append_metadata_row(
            stage_name=stage_name,
            city=city,
            row_count_in=row_count_in,
            row_count_out=result.row_count_out,
            status=status,
            duration_seconds=duration_seconds,
        )
