import sys
from unittest.mock import MagicMock, call
import pytest

from models import RFIDTag

# Mock missing modules globally
MOCK_MODULES = [
    "busio",
    "board",
    "adafruit_pn532",
    "adafruit_pn532.spi",
    "digitalio",
    "audio",
    "rfidreaders",
    "neopixel"
]

for module_name in MOCK_MODULES:
    sys.modules[module_name] = MagicMock()

@pytest.fixture
def players():
    """Fixture to provide a list of players."""
    return [
        RFIDTag(rfid_tag="4-216-28-234", name="Ritter", rfid_type="figure"),
        RFIDTag(rfid_tag="4-200-28-234", name="Königin", rfid_type="figure"),
        RFIDTag(rfid_tag="4-192-28-234", name="Frau", rfid_type="figure"),
    ]

def filter_calls(calls):
    return [c for c in calls.mock_calls if c != call.__str__()]