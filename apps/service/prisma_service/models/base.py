"""Shared validation policy for HTTP models."""

from pydantic import BaseModel, ConfigDict


class ApiModel(BaseModel):
    """Reject unknown fields so malformed research data is not ignored silently."""

    model_config = ConfigDict(extra="forbid")
