import logging
from pathlib import Path
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, HttpUrl, field_validator

logger = logging.getLogger(__name__)


class Project(BaseModel):
    """
    Represents a single source code repository to be scanned.
    """

    id: UUID = Field(
        default_factory=uuid4, description="Unique identifier for the project."
    )
    url: str = Field(..., description="The Git URL or local path of the repository.")
    name: str = Field(..., description="The name of the repository.")
    language: str | None = Field(
        None, description="Primary programming language of the project."
    )
    description: str | None = Field(
        None, description="Brief description of the project."
    )
    languages: list[str] = Field(
        default_factory=list,
        description="A list of programming languages detected in the project.",
    )

    # Optional network configuration for DAST egress control and targeting
    network_allow_hosts: list[str] = Field(
        default_factory=list,
        description="Optional list of allowed host:port entries (e.g., '127.0.0.1:8080', 'localhost:3000') for DAST.",
    )
    network_allow_ip_ranges: list[str] = Field(
        default_factory=list,
        description="Optional list of CIDR ranges allowed for DAST egress (e.g., '127.0.0.1/32').",
    )
    ports: list[str] = Field(
        default_factory=list,
        description="Optional list of ports relevant for the project's HTTP services (strings to avoid type issues).",
    )

    @field_validator("url")
    @classmethod
    def validate_url_or_path(cls, v: str) -> str:
        """Allow both HTTP URLs and local file paths."""
        if isinstance(v, str) and v.strip():  # Must be non-empty string
            # Check if it's a local path
            if v.startswith("/") or Path(v).exists():
                return v
            # Try to validate as URL
            try:
                HttpUrl(v)
                return v
            except Exception:
                # If it's not a valid URL and not a local path, it might still be a relative path
                # Log warning for potentially invalid URLs
                logger.warning(f"URL '{v}' doesn't match expected patterns, allowing for flexibility")
                return v
        raise ValueError("URL must be a non-empty string")

    def __str__(self) -> str:
        return f"Project(name={self.name}, url={self.url}, language={self.language})"
