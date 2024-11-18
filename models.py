from dataclasses import dataclass

@dataclass
class RFIDTag:
    rfid_tag: str
    name: str
    rfid_type: str
    number: int | None = None
