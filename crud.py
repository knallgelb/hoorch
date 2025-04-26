from sqlmodel import Session, select
from database import get_db
from models import Usage

def add_game_entry(usage: Usage, db: Session = next(get_db())):
    db.add(usage)
    db.commit()
    db.refresh(usage)

def get_all_games(db: Session = next(get_db())):
    return db.exec(select(Usage)).all()

def get_all_games_to_submit(db: Session = next(get_db())):
    return db.exec(select(Usage).filter(Usage.is_transmitted == False)).all()

def set_transmitted(usage: Usage, db: Session = next(get_db())):
    u: Usage | None = db.exec(select(Usage).where(Usage.id == usage.id)).first()
    if u is None:
        return None
    u.is_transmitted = True
    db.add(u)
    db.commit()
    db.refresh(u)
    return u
