import os

from KOV.runtime.privacy import apply_local_privacy_defaults


def test_privacy_defaults_disable_content_capture(monkeypatch) -> None:
    keys = (
        "ADK_CAPTURE_MESSAGE_CONTENT_IN_SPANS",
        "OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT",
        "OTEL_TRACES_EXPORTER",
        "OTEL_METRICS_EXPORTER",
        "OTEL_LOGS_EXPORTER",
    )
    for key in keys:
        monkeypatch.delenv(key, raising=False)

    apply_local_privacy_defaults()

    assert os.environ["ADK_CAPTURE_MESSAGE_CONTENT_IN_SPANS"] == "false"
    assert os.environ["OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT"] == "NO_CONTENT"
    assert os.environ["OTEL_TRACES_EXPORTER"] == "none"
    assert os.environ["OTEL_METRICS_EXPORTER"] == "none"
    assert os.environ["OTEL_LOGS_EXPORTER"] == "none"


def test_privacy_defaults_override_content_capture_enablement(monkeypatch) -> None:
    monkeypatch.setenv("ADK_CAPTURE_MESSAGE_CONTENT_IN_SPANS", "true")
    apply_local_privacy_defaults()
    assert os.environ["ADK_CAPTURE_MESSAGE_CONTENT_IN_SPANS"] == "false"
