from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import datetime

class UsageTransfer(BaseModel):
    game: str
    players: int
    box_id: UUID
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)
