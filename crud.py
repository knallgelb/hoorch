from sqlmodel import Session, select
from pathlib import Path

from database import get_db, engine
from models import Usage, RFIDTag
from logger_util import get_logger

logger = get_logger(__name__, "logs/crud.log")


def add_game_entry(usage: Usage, db: Session = next(get_db())):
    db.add(usage)
    db.commit()
    db.refresh(usage)
    logger.debug(f"Game entry added: {usage}")


def get_all_games(db: Session = next(get_db())):
    games = db.exec(select(Usage)).all()
    logger.debug(f"Retrieved {len(games)} games from database.")
    return games


def get_all_games_to_submit(db: Session = next(get_db())):
    games = db.exec(select(Usage).filter(Usage.is_transmitted == False)).all()
    logger.debug(f"Retrieved {len(games)} games to submit from database.")
    return games


def set_transmitted(usage: Usage, db: Session = next(get_db())):
    u: Usage | None = db.exec(select(Usage).where(Usage.id == usage.id)).first()
    if u is None:
        logger.warning(f"Usage entry not found with id={usage.id} to set transmitted.")
        return None
    u.is_transmitted = True
    db.add(u)
    db.commit()
    db.refresh(u)
    logger.debug(f"Usage entry set as transmitted: {u}")
    return u


def initialize_rfid_tags():
    CATEGORY_FILES = [
        "actions.txt",
        "animals.txt",
        "figures.txt",
        "games.txt",
        "numeric.txt",
    ]
    FIGURES_PATH = "./figures"

    with Session(engine) as session:
        for filename in CATEGORY_FILES:
            category = filename.split(".")[0]
            file_path = Path(FIGURES_PATH) / filename
            if not file_path.exists():
                continue

            with file_path.open("r", encoding="utf-8") as f:
                lines = [line.strip() for line in f if line.strip()]

            if category == "numeric":
                # For numeric category, insert all entries including duplicates
                for name in lines:
                    number = None
                    try:
                        number = int(name)
                    except ValueError:
                        number = None

                    # Check how many tags with this number already exist
                    count_existing = session.exec(
                        select(RFIDTag).where(RFIDTag.number == number)
                    ).count()

                    if count_existing < 2:
                        new_tag = RFIDTag(
                            rfid_tag='',
                            name=name,
                            rfid_type=category,
                            number=number,
                        )
                        session.add(new_tag)
            else:
                for name in lines:
                    existing = session.exec(
                        select(RFIDTag).where(RFIDTag.name == name, RFIDTag.rfid_type == category)
                    ).first()
                    if existing:
                        continue

                    number = None
                    new_tag = RFIDTag(
                        rfid_tag='',
                        name=name,
                        rfid_type=category,
                        number=number,
                    )
                    session.add(new_tag)
        session.commit()


# --- CRUD functions for RFIDTag ---


def get_rfid_tag_by_id(rfid_tag_id: str, db: Session = next(get_db())) -> RFIDTag | None:
    tag = db.exec(select(RFIDTag).where(RFIDTag.rfid_tag == rfid_tag_id)).first()
    if tag:
        logger.debug(f"Found RFIDTag by id: {rfid_tag_id}")
    else:
        logger.debug(f"RFIDTag not found by id: {rfid_tag_id}")
    return tag


def get_all_rfid_tags(db: Session = next(get_db())) -> list[RFIDTag]:
    tags = db.exec(select(RFIDTag)).all()
    logger.debug(f"Retrieved {len(tags)} RFIDTags from database.")
    return tags


def create_rfid_tag(tag: RFIDTag, db: Session = next(get_db())) -> RFIDTag | None:
    existing = db.exec(select(RFIDTag).where(RFIDTag.rfid_tag == tag.rfid_tag)).first()
    if existing:
        logger.warning(f"Attempt to create already existing RFIDTag: {tag.rfid_tag}")
        return None
    db.add(tag)
    db.commit()
    db.refresh(tag)
    logger.debug(f"Created new RFIDTag: {tag}")
    return tag


def update_rfid_tag_by_id(rfid_tag_id: str, updated_tag: RFIDTag, db: Session = next(get_db())) -> RFIDTag | None:
    tag = db.exec(select(RFIDTag).where(RFIDTag.rfid_tag == rfid_tag_id)).first()
    if not tag:
        logger.warning(f"RFIDTag not found for update: {rfid_tag_id}")
        return None
    tag.name = updated_tag.name
    tag.rfid_type = updated_tag.rfid_type
    tag.number = updated_tag.number
    db.add(tag)
    db.commit()
    db.refresh(tag)
    logger.debug(f"Updated RFIDTag {rfid_tag_id} to new values: {updated_tag}")
    return tag


def delete_rfid_tag_by_id(rfid_tag_id: str, db: Session = next(get_db())) -> bool:
    tag = db.exec(select(RFIDTag).where(RFIDTag.rfid_tag == rfid_tag_id)).first()
    if not tag:
        logger.warning(f"RFIDTag not found to delete: {rfid_tag_id}")
        return False
    db.delete(tag)
    db.commit()
    logger.debug(f"Deleted RFIDTag: {rfid_tag_id}")
    return True
