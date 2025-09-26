from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from src.models.finding import Finding


class Scan(BaseModel):
    """
    Represents a single scan execution for a project.
    """
    id: UUID = Field(default_factory=uuid4, description="Unique identifier for the scan.")
    projectId: UUID = Field(..., description="Foreign key to the Project entity.")
    timestamp: datetime = Field(default_factory=datetime.now, description="The time the scan was initiated.")
    status: str = Field(..., description="The current status of the scan (e.g., 'pending', 'in_progress', 'completed', 'failed').")
    results: list[Finding] = Field(default_factory=list, description="A list of findings from the scan.")
