"""Benchmark infrastructure for measuring harmonization quality."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel, Field

from geotcha import __version__
from geotcha.harmonize.rules import harmonize_gse, harmonize_gsm
from geotcha.models import GSERecord, GSMRecord

logger = logging.getLogger(__name__)

# Fields to benchmark at GSE level
GSE_FIELDS = ("tissue", "disease", "treatment", "timepoint")
# Fields to benchmark at GSM level
GSM_FIELDS = ("tissue", "disease", "gender", "age", "treatment", "timepoint", "cell_type")


class FieldMetrics(BaseModel):
    """Metrics for a single harmonized field."""

    total: int = 0
    correct: int = 0
    present: int = 0
    has_ontology_id: int = 0
    exact_match: float = 0.0
    completeness: float = 0.0
    ontology_coverage: float = 0.0
    mean_confidence: float = 0.0


class BenchmarkResult(BaseModel):
    """Full benchmark result."""

    benchmark_version: str = __version__
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    ml_mode: str = "off"
    fixture_count: int = 0
    summary: dict[str, float] = Field(default_factory=dict)
    per_field: dict[str, FieldMetrics] = Field(default_factory=dict)
    errors: list[dict] = Field(default_factory=list)


def load_fixtures(fixture_dir: Path) -> list[dict]:
    """Load benchmark fixtures from a directory with an index.json."""
    index_path = fixture_dir / "index.json"
    if not index_path.exists():
        raise FileNotFoundError(f"No index.json found in {fixture_dir}")
    filenames = json.loads(index_path.read_text())
    fixtures = []
    for fname in filenames:
        fpath = fixture_dir / fname
        if fpath.exists():
            fixtures.append(json.loads(fpath.read_text()))
        else:
            logger.warning(f"Fixture file not found: {fpath}")
    return fixtures


def _build_gse_record(fixture: dict) -> GSERecord:
    """Build a GSERecord from fixture input data."""
    inp = fixture["input"]
    samples = []
    for s in fixture.get("samples", []):
        si = s["input"]
        samples.append(GSMRecord(
            gsm_id=s["gsm_id"],
            gse_id=fixture["gse_id"],
            tissue=si.get("tissue"),
            cell_type=si.get("cell_type"),
            disease=si.get("disease"),
            gender=si.get("gender"),
            age=si.get("age"),
            treatment=si.get("treatment"),
            timepoint=si.get("timepoint"),
        ))
    return GSERecord(
        gse_id=fixture["gse_id"],
        title=inp.get("title", ""),
        summary=inp.get("summary", ""),
        tissue=inp.get("tissue"),
        disease=inp.get("disease"),
        treatment=inp.get("treatment"),
        timepoint=inp.get("timepoint"),
        cell_type=inp.get("cell_type"),
        samples=samples,
    )


def _compare_field(actual: str | None, expected: str | None) -> bool:
    """Case-insensitive comparison of harmonized values."""
    if actual is None and expected is None:
        return True
    if actual is None or expected is None:
        return False
    return actual.strip().lower() == expected.strip().lower()


def run_benchmark(
    fixtures: list[dict],
    settings=None,
    ml_mode: str = "off",
) -> BenchmarkResult:
    """Run benchmark on fixtures and compute metrics."""
    ml_harmonizer = None
    if ml_mode != "off" and settings is not None:
        try:
            from geotcha.ml.inference import MLHarmonizer
            ml_harmonizer = MLHarmonizer.from_config(settings)
        except Exception as e:
            logger.warning(f"ML models could not be loaded: {e}")

    result = BenchmarkResult(ml_mode=ml_mode, fixture_count=len(fixtures))

    # Accumulators per field
    field_data: dict[str, dict] = {}
    for f in (*GSE_FIELDS, *GSM_FIELDS):
        if f not in field_data:
            field_data[f] = {
                "total": 0, "correct": 0, "present": 0,
                "has_ont": 0, "confidences": [],
            }

    for fixture in fixtures:
        record = _build_gse_record(fixture)
        record = harmonize_gse(record)
        record.samples = [harmonize_gsm(s) for s in record.samples]

        if ml_harmonizer is not None:
            try:
                record = ml_harmonizer.harmonize_gse(record)
                record.samples = [ml_harmonizer.harmonize_gsm(s) for s in record.samples]
            except Exception:
                pass

        expected = fixture.get("expected", {})

        # GSE-level comparison
        for field in GSE_FIELDS:
            exp_key = f"{field}_harmonized"
            exp_val = expected.get(exp_key)
            if exp_val is None:
                continue
            actual_val = getattr(record, f"{field}_harmonized", None)
            conf = getattr(record, f"{field}_confidence", None)
            ont_id = getattr(record, f"{field}_ontology_id", None)

            fd = field_data[field]
            fd["total"] += 1
            if actual_val is not None:
                fd["present"] += 1
            if ont_id:
                fd["has_ont"] += 1
            if conf is not None:
                fd["confidences"].append(conf)
            if _compare_field(actual_val, exp_val):
                fd["correct"] += 1
            else:
                result.errors.append({
                    "fixture": fixture["gse_id"],
                    "level": "gse",
                    "field": field,
                    "expected": exp_val,
                    "actual": actual_val,
                })

        # GSM-level comparison
        for sample_fixture, sample_record in zip(
            fixture.get("samples", []), record.samples
        ):
            s_expected = sample_fixture.get("expected", {})
            for field in GSM_FIELDS:
                exp_key = f"{field}_harmonized"
                exp_val = s_expected.get(exp_key)
                if exp_val is None:
                    continue
                actual_val = getattr(sample_record, f"{field}_harmonized", None)
                conf = getattr(sample_record, f"{field}_confidence", None)
                ont_id = getattr(sample_record, f"{field}_ontology_id", None)

                fd = field_data[field]
                fd["total"] += 1
                if actual_val is not None:
                    fd["present"] += 1
                if ont_id:
                    fd["has_ont"] += 1
                if conf is not None:
                    fd["confidences"].append(conf)
                if _compare_field(actual_val, exp_val):
                    fd["correct"] += 1
                else:
                    result.errors.append({
                        "fixture": fixture["gse_id"],
                        "level": "gsm",
                        "sample": sample_fixture["gsm_id"],
                        "field": field,
                        "expected": exp_val,
                        "actual": actual_val,
                    })

    # Compute per-field metrics
    total_correct = 0
    total_total = 0
    total_present = 0
    total_ont = 0
    for field, fd in field_data.items():
        if fd["total"] == 0:
            continue
        metrics = FieldMetrics(
            total=fd["total"],
            correct=fd["correct"],
            present=fd["present"],
            has_ontology_id=fd["has_ont"],
            exact_match=round(fd["correct"] / fd["total"], 4) if fd["total"] else 0,
            completeness=round(fd["present"] / fd["total"], 4) if fd["total"] else 0,
            ontology_coverage=round(fd["has_ont"] / fd["total"], 4) if fd["total"] else 0,
            mean_confidence=(
                round(sum(fd["confidences"]) / len(fd["confidences"]), 4)
                if fd["confidences"]
                else 0.0
            ),
        )
        result.per_field[field] = metrics
        total_correct += fd["correct"]
        total_total += fd["total"]
        total_present += fd["present"]
        total_ont += fd["has_ont"]

    if total_total > 0:
        result.summary = {
            "overall_exact_match": round(total_correct / total_total, 4),
            "overall_completeness": round(total_present / total_total, 4),
            "overall_ontology_coverage": round(total_ont / total_total, 4),
        }

    return result


def write_report(result: BenchmarkResult, output_path: Path) -> Path:
    """Write benchmark report to a JSON file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(result.model_dump_json(indent=2))
    return output_path
