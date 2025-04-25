from dataclasses import dataclass
from operator import imod
from sqlmodel import SQLModel, Field
from typing import Optional, List
from datetime import datetime
import os
from dotenv import load_dotenv

dotenv_path = "/home/pi/hoorch/.env"
load_dotenv(dotenv_path, override=True)

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
    game: str
    players: int
    box_id: str = Field(default=os.getenv("HOORCH_UID"))
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    is_transmitted: bool = Field(default=False)
