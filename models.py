from dataclasses import dataclass
from sqlmodel import SQLModel, Field
from typing import Optional, List
from datetime import datetime

# @dataclass(frozen=True)
@dataclass
class RFIDTag:
    rfid_tag: str
    name: str
    rfid_type: str
    number: int | None = None

    def __hash__(self):
        return hash((self.rfid_tag, self.name, self.rfid_type, self.number))

class Usage(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    box_id: str
    game: str
    players: int
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    is_transmitted: bool = Field(default=False)
