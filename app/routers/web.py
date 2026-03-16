from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse

router = APIRouter(tags=["Web"])

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


@router.get("/", include_in_schema=False)
def web_root():
    return FileResponse(STATIC_DIR / "index.html")


@router.get("/sistema", include_in_schema=False)
def web_system():
    return FileResponse(STATIC_DIR / "index.html")
