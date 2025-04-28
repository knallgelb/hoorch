import httpx
import crud
import os
import models
from schemas import UsageTransfer
from dotenv import load_dotenv

dotenv_path = "/home/pi/hoorch/.env"
load_dotenv(dotenv_path, override=True)

def has_internet_connection(url='https://www.google.com/', timeout=3):
    try:
        httpx.head(url, timeout=timeout)
        return True
    except Exception:
        return False

def send_and_update_stats():
    # Prüfe Internetverbindung BEVOR wir senden:
    if not has_internet_connection():
        print("Keine Internetverbindung – Daten werden nicht gesendet.")
        return

    usages = crud.get_all_games_to_submit()
    for usage in usages:
        send_single_usage(usage)

def send_single_usage(usage: models.Usage):
    usage_transfer = UsageTransfer.model_validate(usage)
    r = httpx.post(os.getenv('STATS_URL'), json=usage_transfer.model_dump(mode="json"))
    data = r.json()
    if data["message"] == "created_usage":
        u = crud.set_transmitted(usage)
        return u

if __name__ == '__main__':
    send_and_update_stats()
