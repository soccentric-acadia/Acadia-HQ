from typing import Any

from pydantic import BaseModel, Field, field_validator


class ConfigurationWrite(BaseModel):
    """Opaque configuration document until the Configuration contract lands."""

    values: dict[str, Any] = Field(default_factory=dict)

    @field_validator("values")
    @classmethod
    def validate_values(cls, value: dict[str, Any]) -> dict[str, Any]:
        if len(value) > 256:
            raise ValueError("configuration has too many top-level keys")
        return value
