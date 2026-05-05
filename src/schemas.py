from typing import Any

from pydantic import BaseModel, Field


class SafetyVerdict(BaseModel):
    blocked: bool
    category: str = "safe"
    message: str = ""


class ClassificationResult(BaseModel):
    intent: str
    agent: str
    entities: dict[str, Any] = Field(default_factory=dict)
    safety: dict[str, str] = Field(
        default_factory=lambda: {"verdict": "safe", "reason": "passed local guard"}
    )
