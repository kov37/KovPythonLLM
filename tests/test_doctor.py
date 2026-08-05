from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from KOV.diagnostics.doctor import (
    CheckResult,
    CheckStatus,
    DoctorReport,
    _normalize_remote,
    _parse_num_ctx,
)


def test_parse_num_ctx_from_modelfile() -> None:
    modelfile = "FROM /models/blob\nPARAMETER temperature 0\nPARAMETER num_ctx 32768\n"
    assert _parse_num_ctx(modelfile) == 32_768


def test_parse_num_ctx_rejects_missing_value() -> None:
    assert _parse_num_ctx("PARAMETER temperature 0\n") is None


def test_remote_normalization_ignores_git_suffix() -> None:
    assert _normalize_remote("https://github.com/kov37/KovPythonLLM.git\n") == (
        "https://github.com/kov37/KovPythonLLM"
    )


def test_report_is_ready_with_warnings() -> None:
    report = DoctorReport.from_checks(
        [
            CheckResult(check_id="test.pass", status=CheckStatus.PASS, summary="ok"),
            CheckResult(check_id="test.warn", status=CheckStatus.WARN, summary="not loaded"),
        ]
    )
    assert report.overall_status is CheckStatus.WARN
    assert report.ready is True
    assert report.generated_at.tzinfo is not None


def test_report_fails_closed() -> None:
    report = DoctorReport.from_checks(
        [CheckResult(check_id="test.fail", status=CheckStatus.FAIL, summary="broken")]
    )
    assert report.overall_status is CheckStatus.FAIL
    assert report.ready is False


def test_check_result_forbids_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        CheckResult.model_validate(
            {
                "check_id": "test.invalid",
                "status": "pass",
                "summary": "ok",
                "unexpected": True,
            },
            strict=True,
        )


def test_report_accepts_explicit_timestamp() -> None:
    report = DoctorReport(
        generated_at=datetime.now(UTC),
        overall_status=CheckStatus.PASS,
        ready=True,
        checks=(),
    )
    assert report.schema_version == "1.0"
