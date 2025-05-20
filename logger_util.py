import logging
import os
from dotenv import load_dotenv

dotenv_path = "/home/pi/hoorch/.env"
load_dotenv(dotenv_path, override=True)


def get_logger(name: str, log_file: str, level: int = logging.DEBUG) -> logging.Logger:
    """
    Erstellt und konfiguriert einen Logger mit dem angegebenen Namen und Logfile-Pfad.

    Parameter:
        name (str): Name des Loggers (z.B. __name__).
        log_file (str): Pfad zur Logdatei.
        level (int): Logging-Level (Standard: logging.DEBUG).

    Rückgabe:
        logging.Logger: Der konfigurierte Logger.
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    debug_mode = os.getenv("DEBUG_MODE", "false").lower() == "true"

    # Verhindert, dass Handler mehrfach hinzugefügt werden, wenn der Logger bereits konfiguriert wurde.
    if not logger.handlers:
        # Erstelle das Verzeichnis für das Logfile, falls es nicht existiert.
        log_dir = os.path.dirname(log_file)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)

        # Erstelle einen Datei-Handler für das Logfile.
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(level)

        # Füge die Handler dem Logger hinzu.
        logger.addHandler(file_handler)

        # Erstelle einen Konsolen-Handler nur wenn DEBUG_MODE true ist.
        if debug_mode:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(level)
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            file_handler.setFormatter(formatter)
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)
        else:
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            file_handler.setFormatter(formatter)

    return logger
