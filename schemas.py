from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import datetime

class UsageTransfer(BaseModel):
    game: str
    players: int
    box_id: UUID
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)

class RFIDTagSchema(BaseModel):
    rfid_tag: str
    name: str
    rfid_type: str
    number: int | None = None

    class Config:
        orm_mode = True
