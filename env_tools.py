import os
from dotenv import load_dotenv

load_dotenv()  # Lädt die .env-Datei

def str_to_bool(value: str) -> bool:
    """
    Konvertiert einen String in einen Boolean.
    Akzeptiert "true", "1", "yes", "on" als True.
    """
    return value.strip().lower() in ("true", "1", "yes", "on")