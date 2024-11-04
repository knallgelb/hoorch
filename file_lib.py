import os
from pathlib import Path
import csv
import re
import logging
from models import RFIDTag

figures_db = dict()     # Figure database is a dictionary with tag ID and tag name
gamer_figures_db = dict()  # e.g., knight, queen,...
animal_figures_db = dict() # e.g., lion, elephant,...
animal_numbers_db = dict() # e.g., 0, 1, 2,...
actions_db = dict() # start, end, etc.

# Create 'logs' directory if it doesn't exist
if not Path('logs').exists():
    os.makedirs('logs')

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

# Create handlers
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)

file_handler = logging.FileHandler('logs/database_from_file.log')
file_handler.setLevel(logging.DEBUG)

# Create formatter and add it to the handlers
formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
console_handler.setFormatter(formatter)
file_handler.setFormatter(formatter)

# Add handlers to the logger
logger.addHandler(console_handler)
logger.addHandler(file_handler)


def read_database_file(path_object: Path, append_to_variable: dict):
    if path_object.exists():
        with open(path_object, mode="r", encoding="utf-8") as file:
            csv_reader = csv.DictReader(file, delimiter=';', fieldnames=["RFID_TAG", "NAME"])
            next(csv_reader)

            for row in csv_reader:
                # Assign column names
                append_to_variable.update({row["RFID_TAG"]: RFIDTag(rfid_tag=row["RFID_TAG"], name=row["NAME"])})
    return append_to_variable


def read_database_files():
    global actions_db, figures_db, gamer_figures_db, animal_figures_db, animal_numbers_db

    path_actions = Path("figures") / "actions_db.txt"
    path_animals = Path("figures") / "animals_db.txt"
    path_figures = Path("figures") / "figures_db.txt"
    path_games = Path("figures") / "games_db.txt"
    path_numbers = Path("figures") / "numeric_db.txt"

    actions_db = read_database_file(path_actions, actions_db)  # Figure database is a dictionary with tag ID and tag name
    figures_db = read_database_file(path_figures, figures_db)  # Figure database is a dictionary with tag ID and tag name
    gamer_figures_db = read_database_file(path_games, gamer_figures_db)  # e.g., knight, queen,...
    animal_figures_db = read_database_file(path_animals, animal_figures_db)  # e.g., lion, elephant,...
    animal_numbers_db = read_database_file(path_numbers, animal_numbers_db)  # e.g., 0, 1, 2, ...


if __name__ == "__main__":
    read_database_files()
    logger.debug(actions_db)
    logger.debug(figures_db)
    logger.debug(gamer_figures_db)
    logger.debug(animal_figures_db)
    logger.debug(animal_numbers_db)