"""Shared diagnostic data structures for analyzer phases."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict


@dataclass(frozen=True)
class SourceLoc:
    line: int = 0
    column: int = 0

    @classmethod
    def from_token(cls, token: Any) -> "SourceLoc":
        return cls(line=getattr(token, "line", 0), column=getattr(token, "column", 0))

    def to_dict(self) -> Dict[str, int]:
        return {"line": self.line, "column": self.column}


@dataclass(frozen=True)
class Diagnostic:
    phase: str
    message: str
    line: int = 0
    column: int = 0

    @classmethod
    def from_loc(cls, phase: str, message: str, loc: SourceLoc) -> "Diagnostic":
        return cls(phase=phase, message=message, line=loc.line, column=loc.column)

    @classmethod
    def from_token(cls, phase: str, message: str, token: Any) -> "Diagnostic":
        return cls(
            phase=phase,
            message=message,
            line=getattr(token, "line", 0),
            column=getattr(token, "column", 0),
        )

    def format(self) -> str:
        phase_label = {
            "lexical": "词法错误",
            "syntax": "语法错误",
            "semantic": "语义错误",
        }.get(self.phase, f"{self.phase}错误")
        return f"Ln {self.line}:{self.column} {phase_label}: {self.message}"

    def to_dict(self) -> Dict[str, object]:
        return {
            "phase": self.phase,
            "message": self.message,
            "line": self.line,
            "column": self.column,
        }
