from typing import Any, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ErrorResponse(BaseModel):
    success: bool = False
    message: str
    error_code: str
    details: dict[str, Any] = Field(default_factory=dict)


class SuccessResponse[T](BaseModel):
    success: bool = True
    message: str = "OK"
    data: T | None = None
