"""Read-only capability broker; no sudo, packages, power, drivers, disk, or kernel."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass

_SERVICES = frozenset({"kov.service", "ollama.service", "research-tutor.service"})


@dataclass(frozen=True, slots=True)
class ServiceStatus:
    service: str
    active_state: str
    sub_state: str
    result: str


class ReadOnlyCapabilityBroker:
    """Intentionally exposes status only; mutations remain outside KOV authority."""

    def service_status(self, service: str) -> ServiceStatus:
        if service not in _SERVICES:
            raise PermissionError("Service is outside the fixed KOV allowlist")
        result = subprocess.run(
            (
                "systemctl",
                "--user",
                "show",
                service,
                "--no-pager",
                "--property=ActiveState,SubState,Result",
            ),
            capture_output=True,
            check=False,
            text=True,
            timeout=5,
        )
        values = dict(line.split("=", 1) for line in result.stdout.splitlines() if "=" in line)
        return ServiceStatus(
            service,
            values.get("ActiveState", "unavailable"),
            values.get("SubState", "unavailable"),
            values.get("Result", "unavailable"),
        )

    def gpu_status(self) -> dict[str, int | None]:
        result = subprocess.run(
            (
                "nvidia-smi",
                "--query-gpu=memory.used,memory.total,utilization.gpu,temperature.gpu",
                "--format=csv,noheader,nounits",
            ),
            capture_output=True,
            check=False,
            text=True,
            timeout=3,
        )
        if result.returncode != 0:
            return {
                "memoryUsedMiB": None,
                "memoryTotalMiB": None,
                "utilization": None,
                "temperatureC": None,
            }
        try:
            values = [int(value.strip()) for value in result.stdout.splitlines()[0].split(",")]
            return dict(
                zip(
                    ("memoryUsedMiB", "memoryTotalMiB", "utilization", "temperatureC"),
                    values,
                    strict=True,
                )
            )
        except (IndexError, ValueError):
            return {
                "memoryUsedMiB": None,
                "memoryTotalMiB": None,
                "utilization": None,
                "temperatureC": None,
            }
