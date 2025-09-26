from enum import Enum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class Severity(str, Enum):
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"
    UNKNOWN = "UNKNOWN"


class Finding(BaseModel):
    """
    Represents a single vulnerability or issue discovered by a tool.
    """

    id: UUID = Field(
        default_factory=uuid4, description="Unique identifier for the finding."
    )
    tool: str = Field(
        ...,
        description="The name of the tool that discovered the finding (e.g., 'Semgrep', 'Trivy', 'OSV-Scanner', 'OWASP ZAP').",
    )
    description: str = Field(..., description="A description of the finding.")
    severity: Severity = Field(
        ...,
        description="The severity level of the finding (e.g., 'High', 'Medium', 'Low').",
    )
    filePath: str = Field(
        ..., description="The path to the file where the finding was discovered."
    )
    lineNumber: int | None = Field(None, description="The line number of the finding.")
    complianceMappings: list[str] = Field(
        default_factory=list,
        description="A list of compliance frameworks the finding maps to (e.g., 'NIST-800-53', 'OWASP-Top-10-2021-A01').",
    )
