from sqlmodel import Session, select
from database import get_db
from models import Usage

def add_game_entry(usage: Usage, db: Session = next(get_db())):
    db.add(usage)
    db.commit()
    db.refresh(usage)

def get_all_games(db: Session = next(get_db())):
    return db.exec(select(Usage)).all()
