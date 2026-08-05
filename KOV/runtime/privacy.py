"""Fail-safe local privacy defaults applied before agent libraries import."""

from __future__ import annotations

import os


def apply_local_privacy_defaults() -> None:
    """Disable ADK message-content capture for every KOV process."""

    os.environ["ADK_CAPTURE_MESSAGE_CONTENT_IN_SPANS"] = "false"
    os.environ["OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT"] = "NO_CONTENT"
    os.environ["OTEL_TRACES_EXPORTER"] = "none"
    os.environ["OTEL_METRICS_EXPORTER"] = "none"
    os.environ["OTEL_LOGS_EXPORTER"] = "none"
