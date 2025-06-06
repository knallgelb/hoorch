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
    tags = dict()
    for i in range(10):  # Zahlen 0-9
        tags.update({f"4-216-28-{2 * i + 1}": RFIDTag(rfid_tag=f"4-216-28-{2 * i + 1}", name=str(i), number=i, rfid_type="number")})
        tags.update({f"4-216-28-{2 * i + 2}": RFIDTag(rfid_tag=f"4-216-28-{2 * i + 2}", name=str(i), number=i, rfid_type="number")})
    return tags


def filter_calls(calls):
    return [c for c in calls.mock_calls if c != call.__str__()]

@pytest.fixture
def mock_file_lib(numbers):
    mock_lib = MagicMock()
    # Beispiel: Wir wollen, dass .animal_numbers_db[0] = numbers[5]
    # und numbers[5] liegt dann in mock_rfidreaders.tags an Index 1 oder 3
    mock_lib.animal_numbers_db = numbers

    return mock_lib


@pytest.fixture
def mock_rfidreaders(numbers):
    mock_readers = MagicMock()
    # Achte darauf, dass an Index 1 oder 3 deines arrays `numbers[5]` liegt.
    # Index:  0           1           2           3           4
    # Inhalt: numbers[0], numbers[5], numbers[8], numbers[7], numbers[9]
    # So liegt an Index 1 = numbers[5] und an Index 3 = numbers[7].
    rfid_numbers = list(numbers.values())
    mock_readers.tags = [rfid_numbers[0], rfid_numbers[5], rfid_numbers[8], rfid_numbers[7], rfid_numbers[9]]
    return mock_readers
