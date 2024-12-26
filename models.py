from dataclasses import dataclass


# @dataclass(frozen=True)
@dataclass
class RFIDTag:
    rfid_tag: str
    name: str
    rfid_type: str
    number: int | None = None

    def __hash__(self):
        return hash((self.rfid_tag, self.name, self.rfid_type, self.number))