from typing import Dict, Optional

from models import RFIDTag
from crud import get_all_rfid_tags, get_rfid_tag_by_id
from logger_util import get_logger

logger = get_logger(__name__, "logs/file_lib.log")


def load_all_tags() -> Dict[str, RFIDTag]:
    """Load all RFID tags from the database using CRUD."""
    tags = get_all_rfid_tags()
    tag_dict = {tag.rfid_tag: tag for tag in tags if tag.rfid_tag}
    logger.debug(f"Loaded {len(tag_dict)} RFIDTag entries from DB")
    return tag_dict


def get_figure_from_database(rfid_tag: str) -> Optional[RFIDTag]:
    """Get RFIDTag by rfid_tag value."""
    tag = get_rfid_tag_by_id(rfid_tag)
    if tag:
        logger.debug(f"Found tag for RFID {rfid_tag}")
    else:
        logger.debug(f"No tag found for RFID {rfid_tag}")
    return tag


def group_tags_by_type() -> tuple[Dict[str, RFIDTag], Dict[str, RFIDTag], Dict[str, RFIDTag], Dict[str, RFIDTag], Dict[str, RFIDTag]]:
    """Group all tags by their rfid_type into separate dictionaries."""
    tags = load_all_tags()
    actions_db = {tag.rfid_tag: tag for tag in tags.values() if tag.rfid_type == "action"}
    figures_db = {tag.rfid_tag: tag for tag in tags.values() if tag.rfid_type == "figure"}
    gamer_figures_db = {tag.rfid_tag: tag for tag in tags.values() if tag.rfid_type == "game"}
    animal_figures_db = {tag.rfid_tag: tag for tag in tags.values() if tag.rfid_type == "animal"}
    animal_numbers_db = {tag.rfid_tag: tag for tag in tags.values() if tag.rfid_type == "numeric"}
    logger.debug(f"Grouped tags by type: action={len(actions_db)}, figure={len(figures_db)}, game={len(gamer_figures_db)}, animal={len(animal_figures_db)}, numeric={len(animal_numbers_db)}")
    return actions_db, figures_db, gamer_figures_db, animal_figures_db, animal_numbers_db


def check_tag_attribute(tags, value, attribute='name'):
    """
    Checks if any RFIDTag in the tags list has a specific attribute value.

    :param tags: List of RFIDTag instances.
    :param value: The value to check for (e.g., "ENDE", "JA", "NEIN").
    :param attribute: The attribute of RFIDTag to check (default is 'name').
    :return: True if any tag has the specified attribute value, False otherwise.
    """
    return any(
        tag for tag in tags
        if tag is not None and getattr(tag, attribute, None) == value
    )


if __name__ == "__main__":
    all_tags_db = load_all_tags()
    logger.debug("Alle Tags aus der DB:")
    for tag_id, tag in all_tags_db.items():
        logger.debug(f"RFID_TAG: {tag.rfid_tag}, Attribute: {tag.__dict__}")

    actions_db, figures_db, gamer_figures_db, animal_figures_db, animal_numbers_db = group_tags_by_type()

    logger.debug("Actions DB:")
    for tag_id, tag in actions_db.items():
        logger.debug(f"RFID_TAG: {tag.rfid_tag}, Name: {tag.name}")