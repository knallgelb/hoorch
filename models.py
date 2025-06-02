from dataclasses import dataclass
from operator import imod
from sqlmodel import SQLModel, Field
from typing import Optional, List
from datetime import datetime
import os
from dotenv import load_dotenv

dotenv_path = "/home/pi/hoorch/.env"
load_dotenv(dotenv_path, override=True)

class RFIDTag(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    rfid_tag: str
    name: str
    rfid_type: str

    def __eq__(self, other):
        if not isinstance(other, RFIDTag):
            return NotImplemented
        return (self.id == other.id and
                self.rfid_tag == other.rfid_tag and
                self.name == other.name and
                self.rfid_type == other.rfid_type and
                )

    def __hash__(self):
        return hash((self.id, self.rfid_tag, self.name, self.rfid_type))


class Usage(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    game: str
    players: int
    box_id: str = Field(default=os.getenv("HOORCH_UID"))
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    is_transmitted: bool = Field(default=False)
