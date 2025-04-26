import httpx
import crud
import os
import models
from schemas import UsageTransfer

from dotenv import load_dotenv
dotenv_path = "/home/pi/hoorch/.env"
load_dotenv(dotenv_path, override=True)

def send_and_update_stats():
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
