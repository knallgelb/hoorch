import os
from pathlib import Path
import csv
import re
import logging
from models import RFIDTag

# Initialisiere die Datenbanken als leere Dictionaries
figures_db = dict()
gamer_figures_db = dict()
animal_figures_db = dict()
animal_numbers_db = dict()
actions_db = dict()
all_tags = dict()

# Logging konfigurieren
if not Path('logs').exists():
    os.makedirs('logs')

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)

file_handler = logging.FileHandler('logs/database_from_file.log')
file_handler.setLevel(logging.DEBUG)

formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
console_handler.setFormatter(formatter)
file_handler.setFormatter(formatter)

logger.addHandler(console_handler)
logger.addHandler(file_handler)


def get_figure_from_database(rfid_tag) -> RFIDTag:
    return all_tags.get(rfid_tag)


def read_database_file(path_object: Path,
                       category_dict: dict,
                       all_tags: dict,
                       which_field: str = "name",
                       rfid_type: str = ""):
    if path_object.exists():
        with open(path_object, mode="r", encoding="utf-8") as file:
            csv_reader = csv.DictReader(file, delimiter=';', fieldnames=["RFID_TAG", "NAME"])
            next(csv_reader)

            for row in csv_reader:
                field_value = row["NAME"]
                kwargs = {'rfid_tag': row["RFID_TAG"], which_field: field_value, "rfid_type": rfid_type}

                rfid_tag = row["RFID_TAG"]

                existing_tag = all_tags.get(rfid_tag)
                if existing_tag:
                    setattr(existing_tag, which_field, field_value)
                else:
                    existing_tag = RFIDTag(**kwargs)
                    all_tags[rfid_tag] = existing_tag

                category_dict[rfid_tag] = existing_tag
    else:
        logger.warning(f"Datei {path_object} existiert nicht.")
    return category_dict


def read_database_files():
    global actions_db, figures_db, gamer_figures_db, animal_figures_db, animal_numbers_db, all_tags

    all_tags = {}
    actions_db = {}
    figures_db = {}
    gamer_figures_db = {}
    animal_figures_db = {}
    animal_numbers_db = {}

    path_actions = Path("figures") / "actions_db.txt"
    path_animals = Path("figures") / "animals_db.txt"
    path_figures = Path("figures") / "figures_db.txt"
    path_games = Path("figures") / "games_db.txt"
    path_numbers = Path("figures") / "numeric_db.txt"

    actions_db = read_database_file(path_actions, actions_db, all_tags, rfid_type="action")
    figures_db = read_database_file(path_figures, figures_db, all_tags, rfid_type="figure")
    gamer_figures_db = read_database_file(path_games, gamer_figures_db, all_tags, rfid_type="game")
    animal_figures_db = read_database_file(path_animals, animal_figures_db, all_tags, rfid_type="animal")
    animal_numbers_db = read_database_file(path_numbers, animal_numbers_db, all_tags, which_field='number', rfid_type="number")


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
    read_database_files()
    logger.debug("Alle Tags:")
    for tag_id, tag in all_tags.items():
        logger.debug(f"RFID_TAG: {tag.rfid_tag}, Attribute: {tag.__dict__}")

    # Beispiel: Ausgabe der Tags pro Kategorie
    logger.debug("Actions DB:")
    for tag_id, tag in actions_db.items():
        logger.debug(f"RFID_TAG: {tag.rfid_tag}, Name: {getattr(tag, 'name', None)}")
