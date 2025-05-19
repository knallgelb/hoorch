from fastapi import FastAPI, File, UploadFile, HTTPException, Depends, Request
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.status import HTTP_303_SEE_OTHER
from sqlmodel import Session, select
import os
import shutil
from typing import List

from hoorch.models import RFIDTag
from hoorch.schemas import BaseModel, RFIDTagSchema
from hoorch.database import get_db

import csv
from pathlib import Path

UPLOAD_FOLDER = './data/hoerspiele'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)



FIGURES_PATH = "./hoorch/figures"
CATEGORY_FILES = [
    "actions.txt",
    "animals.txt",
    "figures.txt",
    "games.txt",
    "numeric.txt",
]

app = FastAPI()

# Serve static files (uploaded files) for download
app.mount("/files", StaticFiles(directory=UPLOAD_FOLDER), name="files")

templates = Jinja2Templates(directory="templates")

ALLOWED_EXTENSIONS = {'mp3'}


@app.post("/rfid/init")
async def initialize_rfid_tags(db: Session = Depends(get_db)):
    """
    Creates RFIDTag entries in the DB for all names in the category files with empty rfid_tag field.
    Does not overwrite existing entries with the same name and type.
    """
    created = []
    for filename in CATEGORY_FILES:
        category = filename.split(".")[0]
        file_path = Path(FIGURES_PATH) / filename
        if not file_path.exists():
            continue

        with file_path.open("r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip()]

        for name in lines:
            # Check if a tag with this name and category already exists
            existing = db.exec(
                select(RFIDTag).where(RFIDTag.name == name, RFIDTag.rfid_type == category)
            ).first()
            if existing:
                continue

            # For numeric category, try to parse number
            number = None
            if category == "numeric":
                try:
                    number = int(name)
                except ValueError:
                    number = None

            new_tag = RFIDTag(
                rfid_tag='',
                name=name,
                rfid_type=category,
                number=number,
            )
            db.add(new_tag)
            created.append(name)

    db.commit()
    return {"created_tags": created}
def allowed_file(filename: str) -> bool:
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.get("/", response_class=HTMLResponse)
async def read_index(request: Request):
    files = os.listdir(UPLOAD_FOLDER)
    return templates.TemplateResponse("index.html", {"request": request, "files": files})


@app.post("/", response_class=HTMLResponse)
async def upload_file(request: Request, file: UploadFile = File(...)):
    if not allowed_file(file.filename):
        return HTMLResponse("Invalid file format", status_code=400)
    filename = os.path.basename(file.filename)
    file_location = os.path.join(UPLOAD_FOLDER, filename)
    with open(file_location, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return RedirectResponse(url='/', status_code=HTTP_303_SEE_OTHER)


@app.get("/download/{filename}")
async def download_file(filename: str):
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path=filepath, filename=filename, media_type='application/octet-stream')


@app.get("/rfid/", response_model=List[RFIDTagSchema])
async def list_rfid_tags(db: Session = Depends(get_db)):
    statement = select(RFIDTag)
    results = db.exec(statement).all()
    return results

@app.post("/rfid/", response_model=RFIDTagSchema)
async def create_rfid_tag(tag: RFIDTagSchema, db: Session = Depends(get_db)):
    existing = db.exec(select(RFIDTag).where(RFIDTag.rfid_tag == tag.rfid_tag)).first()
    if existing:
        raise HTTPException(status_code=400, detail="RFID tag already exists")
    db_tag = RFIDTag(
        rfid_tag=tag.rfid_tag,
        name=tag.name,
        rfid_type=tag.rfid_type,
        number=tag.number,
    )
    db.add(db_tag)
    db.commit()
    db.refresh(db_tag)
    return db_tag


@app.get("/rfid/{tag_id}", response_model=RFIDTagSchema)
async def get_rfid_tag(tag_id: str, db: Session = Depends(get_db)):
    tag = db.exec(select(RFIDTag).where(RFIDTag.rfid_tag == tag_id)).first()
    if not tag:
        raise HTTPException(status_code=404, detail="RFID tag not found")
    return tag


@app.put("/rfid/{tag_id}", response_model=RFIDTagSchema)
async def update_rfid_tag(tag_id: str, tag_update: RFIDTagSchema, db: Session = Depends(get_db)):
    tag = db.exec(select(RFIDTag).where(RFIDTag.rfid_tag == tag_id)).first()
    if not tag:
        raise HTTPException(status_code=404, detail="RFID tag not found")

    tag.name = tag_update.name
    tag.rfid_type = tag_update.rfid_type
    tag.number = tag_update.number
    db.add(tag)
    db.commit()
    db.refresh(tag)
    return tag


@app.delete("/rfid/{tag_id}")
async def delete_rfid_tag(tag_id: str, db: Session = Depends(get_db)):
    tag = db.exec(select(RFIDTag).where(RFIDTag.rfid_tag == tag_id)).first()
    if not tag:
        raise HTTPException(status_code=404, detail="RFID tag not found")
    db.delete(tag)
    db.commit()
    return {"detail": "RFID tag deleted"}
