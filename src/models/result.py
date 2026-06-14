from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar("T")


@dataclass(frozen=True)
class Result(Generic[T]):
    success: bool
    value: T | None
    error: str | None

    @classmethod
    def ok(cls, value: T) -> Result[T]:
        return cls(success=True, value=value, error=None)

    @classmethod
    def fail(cls, error: str) -> Result[T]:
        if not error:
            raise ValueError("A failed result must have an error message.")
        return cls(success=False, value=None, error=error)
