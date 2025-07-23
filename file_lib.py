from typing import Dict, Optional
from pathlib import Path

from models import RFIDTag
from crud import (
    get_all_rfid_tags,
    get_rfid_tag_by_id,
    get_all_rfid_tags_by_tag_id,
)
from logger_util import get_logger

logger = get_logger(__name__, "logs/file_lib.log")


def get_file_path(folder: str, filename: str) -> str:
    """
    Returns the full path of an audio file under ./data/<folder>/<filename>.

    :param folder: Subfolder inside the data directory, e.g. 'animal_sounds'
    :param filename: Audio filename, e.g. 'lion.mp3'
    :return: Full path as string
    """
    base_path = Path("./data") / folder / filename
    full_path = base_path.resolve()
    logger.debug(f"Resolved file path for {folder}/{filename}: {full_path}")
    return str(full_path)


def load_all_tags() -> Dict[str, RFIDTag]:
    """Load all RFID tags from the database using CRUD."""
    tags = get_all_rfid_tags()
    tag_dict = {tag.rfid_tag: tag for tag in tags if tag.rfid_tag}
    logger.debug(f"Loaded {len(tag_dict)} RFIDTag entries from DB")
    return tag_dict


def get_tags_by_type(rfid_type: str) -> Dict[str, RFIDTag]:
    """Return a dictionary of RFIDTag objects filtered by rfid_type."""
    tags = get_all_rfid_tags()
    filtered_tags = {
        tag.rfid_tag: tag for tag in tags if tag.rfid_type == rfid_type
    }
    logger.debug(
        f"Loaded {len(filtered_tags)} RFIDTag entries of type '{rfid_type}' from DB"
    )
    return filtered_tags


def get_figure_from_database(rfid_tag: str) -> Optional[RFIDTag]:
    """Get RFIDTag by rfid_tag value."""
    tag = get_rfid_tag_by_id(rfid_tag)
    if tag:
        logger.debug(f"Found tag for RFID {rfid_tag}")
    else:
        logger.debug(f"No tag found for RFID {rfid_tag}")
    return tag


def get_all_figures_by_rfid_tag(rfid_tag: str) -> list[RFIDTag]:
    """
    Fetch all RFIDTag entries from the database matching the given rfid_tag.
    Returns a list of RFIDTag objects.
    """
    # This requires a new CRUD function, e.g. get_all_rfid_tags_by_tag_id to fetch multiple entries
    tags = get_all_rfid_tags_by_tag_id(rfid_tag)
    if tags:
        logger.debug(f"Found {len(tags)} entries for RFID {rfid_tag}")
    else:
        logger.debug(f"No entries found for RFID {rfid_tag}")
    return tags


def check_tag_attribute(tags, value, attribute="name"):
    """
    Checks if any RFIDTag in the tags list has a specific attribute value.

    :param tags: List of RFIDTag instances.
    :param value: The value to check for (e.g., "ENDE", "JA", "NEIN").
    :param attribute: The attribute of RFIDTag to check (default is 'name').
    :return: True if any tag has the specified attribute value, False otherwise.
    """
    return any(
        tag
        for tag in tags
        if tag is not None and getattr(tag, attribute, None) == value
    )


if __name__ == "__main__":
    all_tags_db = load_all_tags()
    logger.debug("Alle Tags aus der DB:")
    for tag_id, tag in all_tags_db.items():
        logger.debug(f"RFID_TAG: {tag.rfid_tag}, Attribute: {tag.__dict__}")

    # Beispielhafte Abfrage
    actions_db = get_tags_by_type("action")
    figures_db = get_tags_by_type("figure")
    gamer_figures_db = get_tags_by_type("games")
    animal_figures_db = get_tags_by_type("animal")
    animal_numbers_db = get_tags_by_type("numeric")

    logger.debug("Actions DB:")
    for tag_id, tag in actions_db.items():
        logger.debug(f"RFID_TAG: {tag.rfid_tag}, Name: {tag.name}")
