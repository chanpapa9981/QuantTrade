from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class RiskCheckResult:
    allowed: bool
    reason: str
