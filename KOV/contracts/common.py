"""Common strict scalar types and identifiers."""

from __future__ import annotations

import re
from typing import Annotated
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, StringConstraints

Identifier = Annotated[
    str,
    StringConstraints(strict=True, min_length=3, max_length=96, pattern=r"^[a-z][a-z0-9_.:-]+$"),
]
Digest = Annotated[
    str,
    StringConstraints(strict=True, min_length=64, max_length=64, pattern=r"^[a-f0-9]{64}$"),
]
RelativePath = Annotated[
    str,
    StringConstraints(strict=True, min_length=1, max_length=4096),
]
EvidenceRef = Annotated[
    str,
    StringConstraints(strict=True, min_length=3, max_length=160, pattern=r"^[a-z][a-z0-9_.:/-]+$"),
]

_PREFIX = re.compile(r"^[a-z][a-z0-9_]{1,20}$")


class StrictModel(BaseModel):
    """Base for contracts that reject coercion and unknown fields."""

    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)


def new_id(prefix: str) -> str:
    """Return an opaque sortable-enough process ID with a validated namespace."""

    if not _PREFIX.fullmatch(prefix):
        raise ValueError(f"Invalid ID prefix: {prefix!r}")
    return f"{prefix}:{uuid4().hex}"
