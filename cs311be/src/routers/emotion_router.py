from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from src.services.emotion_service import EmotionService

router = APIRouter(prefix="/emotion", tags=["emotion"])
_service = EmotionService(cam_index=0, fps=6.0)

class EmotionStartReq(BaseModel):
    session_id: str

@router.post("/start")
def start_emotion(req: EmotionStartReq):
    _service.start_logging(req.session_id)
    return {"ok": True}

@router.post("/stop")
def stop_emotion(req: EmotionStartReq):
    _service.stop_logging(req.session_id)
    return {"ok": True}
