from sqlmodel import Session, select, and_
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
    games = db.exec(select(Usage).order_by(Usage.game)).all()
    logger.debug(f"Retrieved {len(games)} games from database.")
    return games


def get_all_games_to_submit(db: Session = next(get_db())):
    games = db.exec(
        select(Usage).filter(Usage.is_transmitted == False).order_by(Usage.game)
    ).all()
    logger.debug(f"Retrieved {len(games)} games to submit from database.")
    return games


def set_transmitted(usage: Usage, db: Session = next(get_db())):
    u: Usage | None = db.exec(select(Usage).where(Usage.id == usage.id)).first()
    if u is None:
        logger.warning(
            f"Usage entry not found with id={usage.id} to set transmitted."
        )
        return None
    u.is_transmitted = True
    db.add(u)
    db.commit()
    db.refresh(u)
    logger.debug(f"Usage entry set as transmitted: {u}")
    return u


def get_all_rfid_tags_by_tag_id(
    rfid_tag: str, db: Session = next(get_db())
) -> list[RFIDTag]:
    """Fetch all RFIDTag objects matching the given rfid_tag string."""
    tags = db.exec(select(RFIDTag).where(RFIDTag.rfid_tag == rfid_tag)).all()
    logger.debug(
        f"Retrieved {len(tags)} RFIDTags with rfid_tag={rfid_tag} from database."
    )
    return tags


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
                    # Check how many tags with this number already exist
                    count_existing = session.exec(
                        select(RFIDTag)
                        .where(RFIDTag.name == name)
                        .order_by(RFIDTag.name)
                    ).all()
                    count_existing = len(count_existing)

                    if count_existing < 2:
                        new_tag = RFIDTag(
                            rfid_tag="",
                            name=name,
                            rfid_type=category,
                        )
                        session.add(new_tag)
            else:
                for name in lines:
                    # Check if this name already exists for the category in database
                    existing = session.exec(
                        select(RFIDTag)
                        .where(
                            RFIDTag.name == name,
                            RFIDTag.rfid_type == category,
                        )
                        .order_by(RFIDTag.name)
                    ).first()
                    if existing:
                        continue

                    new_tag = RFIDTag(
                        rfid_tag="",
                        name=name,
                        rfid_type=category,
                    )
                    session.add(new_tag)
        session.commit()


# --- CRUD functions for RFIDTag ---


def get_rfid_tag_by_id(
    rfid_tag_id: str, db: Session = next(get_db())
) -> RFIDTag | None:
    tags = db.exec(select(RFIDTag).where(RFIDTag.rfid_tag == rfid_tag_id)).all()
    if not tags:
        logger.debug(f"RFIDTag not found by id: {rfid_tag_id}")
        return None

    combined_tag = RFIDTag(
        id=tags[0].id,
        rfid_tag=rfid_tag_id,
        name=None,
        rfid_type=tags[0].rfid_type if tags else "",
    )

    for tag in tags:
        if tag.name and combined_tag.name is None:
            combined_tag.name = tag.name

    logger.debug(
        f"Found combined RFIDTag by id: {rfid_tag_id} with name: {combined_tag.name}"
    )
    return combined_tag


def get_first_rfid_tag_by_id_and_type(
    rfid_tag_id: str,
    rfid_type: str = "numeric",
    db: Session = next(get_db()),
) -> RFIDTag | None:
    tag = db.exec(
        select(RFIDTag).where(
            (RFIDTag.rfid_tag == rfid_tag_id) & (RFIDTag.rfid_type == rfid_type)
        )
    ).first()
    if tag is None:
        logger.debug(
            f"No RFIDTag found with rfid_tag={rfid_tag_id} and rfid_type={rfid_type}"
        )
    else:
        logger.debug(
            f"Found RFIDTag with rfid_tag={rfid_tag_id} and rfid_type={rfid_type}: {tag}"
        )
    return tag


def get_all_rfid_tags(db: Session = next(get_db())) -> list[RFIDTag]:
    tags = db.exec(select(RFIDTag).order_by(RFIDTag.name)).all()
    logger.debug(f"Retrieved {len(tags)} RFIDTags from database.")
    return tags


def get_all_rfid_tags_by_tag_id(
    rfid_tag: str, db: Session = next(get_db())
) -> list[RFIDTag]:
    tags = db.exec(select(RFIDTag).where(RFIDTag.rfid_tag == rfid_tag)).all()
    logger.debug(
        f"Retrieved {len(tags)} RFIDTags from database for tag_id {rfid_tag}."
    )
    return tags


def create_rfid_tag(
    tag: RFIDTag, db: Session = next(get_db())
) -> RFIDTag | None:
    existing = db.exec(
        select(RFIDTag).where(
            and_(
                RFIDTag.rfid_tag == tag.rfid_tag,
                RFIDTag.rfid_type == tag.rfid_type,
            )
        )
    ).first()
    if existing:
        logger.warning(
            f"Attempt to create already existing RFIDTag: {tag.rfid_tag}"
        )
        return None
    db.add(tag)
    db.commit()
    db.refresh(tag)
    logger.debug(f"Created new RFIDTag: {tag}")
    return tag


def update_rfid_tag_by_id(
    record_id: int, updated_tag: RFIDTag, db: Session = next(get_db())
) -> RFIDTag | None:
    tag = db.exec(select(RFIDTag).where(RFIDTag.id == record_id)).first()
    if not tag:
        logger.warning(f"RFIDTag not found for update id: {record_id}")
        return None
    tag.rfid_tag = updated_tag.rfid_tag
    tag.name = updated_tag.name
    tag.rfid_type = updated_tag.rfid_type
    db.add(tag)
    db.commit()
    db.refresh(tag)
    logger.debug(f"Updated RFIDTag id {record_id} to new values: {updated_tag}")
    return tag


def delete_rfid_tag_by_id(
    rfid_tag_id: str, db: Session = next(get_db())
) -> bool:
    tag = db.exec(
        select(RFIDTag).where(RFIDTag.rfid_tag == rfid_tag_id)
    ).first()
    if not tag:
        logger.warning(f"RFIDTag not found to delete: {rfid_tag_id}")
        return False
    db.delete(tag)
    db.commit()
    logger.debug(f"Deleted RFIDTag: {rfid_tag_id}")
    return True


def get_tags_with_empty_rfid_tag(
    db: Session = next(get_db()),
) -> dict[str, list[RFIDTag]]:
    """
    Returns a dictionary mapping rfid_type to list of RFIDTag objects where rfid_tag is empty or None.
    """
    tags = db.exec(
        select(RFIDTag)
        .where((RFIDTag.rfid_tag == "") | (RFIDTag.rfid_tag == None))
        .order_by(RFIDTag.rfid_type, RFIDTag.name)
    ).all()
    result: dict[str, list[RFIDTag]] = {}
    for tag in tags:
        if tag.rfid_type not in result:
            result[tag.rfid_type] = []
        result[tag.rfid_type].append(tag)
    logger.debug(
        f"Tags with empty rfid_tag: { {k: [t.id for t in v] for k, v in result.items()} }"
    )
    return result
