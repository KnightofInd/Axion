from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.sidebar_service import SidebarService

router = APIRouter()
service = SidebarService()


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=1000)


@router.get("/overview")
async def get_sidebar_overview(email: str, commitments_tab: str = "i_owe") -> dict:
    try:
        return await service.get_overview(email=email, commitments_tab=commitments_tab)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"Sidebar overview failed: {exc}") from exc


@router.post("/sync")
async def sync_sidebar(email: str, resume: bool = True) -> dict:
    try:
        return await service.sync(email=email, resume=resume)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"Sidebar sync failed: {exc}") from exc


@router.post("/ask")
async def ask_sidebar(email: str, body: AskRequest) -> dict:
    try:
        return await service.ask(email=email, question=body.question)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"Sidebar ask failed: {exc}") from exc
