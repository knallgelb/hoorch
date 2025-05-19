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
    number: int | None = None


class Usage(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    game: str
    players: int
    box_id: str = Field(default=os.getenv("HOORCH_UID"))
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    is_transmitted: bool = Field(default=False)
