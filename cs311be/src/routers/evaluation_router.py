# src/routers/evaluation_router.py
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.services.evaluation_service import EvaluationService

router = APIRouter(prefix="/evaluation", tags=["evaluation"])
_service = EvaluationService(base_dir="exports")


class EvaluateReq(BaseModel):
    session_id: str = Field(..., min_length=6)
    role: str | None = "ai_engineer"

    base_dir: str | None = None
    transcript_path: str = ""
    emotion_path: str = ""

    # agent weights
    w_knowledge: float = 0.7
    w_attitude: float = 0.3

    # overall weights (PATCHED)
    w_agent_final: float = 0.65
    w_emotion: float = 0.35


@router.post("/evaluate")
def evaluate(req: EvaluateReq):
    try:
        report = _service.evaluate(
            session_id=req.session_id,
            role=req.role,
            base_dir=req.base_dir,
            transcript_path=req.transcript_path,
            emotion_path=req.emotion_path,
            w_knowledge=req.w_knowledge,
            w_attitude=req.w_attitude,
            w_agent_final=req.w_agent_final,
            w_emotion=req.w_emotion,
        )
        return {"ok": True, "report": report}

    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")
