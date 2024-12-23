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

from i18n import Translator

locale = "de"


@pytest.fixture
def translator_factory():
    """
    Fixture that provides a Translator factory.
    Allows creating a Translator with a specific locale.
    """

    def _translator(locale):
        return Translator(locale=locale, translation_dir="translations")

    return _translator


@pytest.fixture
def players():
    """Fixture to provide a list of players."""
    return [
        RFIDTag(rfid_tag="4-216-28-234", name="Ritter", rfid_type="figure"),
        RFIDTag(rfid_tag="4-200-28-234", name="Königin", rfid_type="figure"),
        RFIDTag(rfid_tag="4-192-28-234", name="Frau", rfid_type="figure"),
    ]


@pytest.fixture
def numbers():
    """Fixture to provide a list of numbers."""
    tags = []
    for i in range(10):  # Zahlen 0-9
        tags.append(RFIDTag(rfid_tag=f"4-216-28-{2 * i + 1}", name=str(i), number=i, rfid_type="number"))
        tags.append(RFIDTag(rfid_tag=f"4-216-28-{2 * i + 2}", name=str(i), number=i, rfid_type="number"))
    return tags


def filter_calls(calls):
    return [c for c in calls.mock_calls if c != call.__str__()]
