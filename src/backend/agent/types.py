from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class AgentTurnResult:
    assistant_message: str
    raw_state: dict[str, Any] | None = None
